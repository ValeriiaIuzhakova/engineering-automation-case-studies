"""
NON-PRODUCTION DEMONSTRATION. Synthetic data only.

An independently written sketch of the ideas behind an LLM bug-classification
pipeline: two-stage classification (area, then type), strict validation of
model output against a versioned taxonomy, confidence-tiered decisions,
idempotent processing, and an append-only audit log.

This is not the production implementation and does not reproduce its code,
prompts, configuration, thresholds, or field names. Thresholds below are
illustrative.

Run:  python3 pipeline.py           (process the synthetic tickets)
      python3 pipeline.py           (run again: everything is skipped)
      python3 pipeline.py --reset   (clear the demo audit log first)
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fake_llm import ScriptedLLM

HERE = Path(__file__).parent

# Illustrative values. In practice these should be set from a calibration
# exercise against human-reviewed labels, not picked up front (see calibration.py).
APPLY_AT = 0.90    # both stages at or above this -> write fields
REVIEW_AT = 0.70   # lowest stage at or above this -> suggest only, ask a human
MAX_ATTEMPTS = 2   # one retry on invalid model output

FALLBACK_VALUES = {"Other (Needs Classification)", "Other"}


# --------------------------------------------------------------------------
# Data shapes
# --------------------------------------------------------------------------

@dataclass
class Ticket:
    key: str
    summary: str
    description: str
    problem_area: Optional[str] = None
    problem_type: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)


@dataclass
class StageResult:
    value: Optional[str]
    confidence: Optional[float]
    reasoning: str
    attempts: int
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class InvalidModelOutput(ValueError):
    pass


# --------------------------------------------------------------------------
# 1. Selection and idempotency
# --------------------------------------------------------------------------

def is_eligible(ticket: Ticket) -> bool:
    """Only tickets with *no* classification at all are processed.

    Selecting "area empty OR type empty" looks equivalent but is not: it
    picks up tickets that already have a value (set by a person or another
    tool), and the pipeline then re-decides it. Requiring both to be empty
    keeps existing values safe.
    """
    return ticket.problem_area is None and ticket.problem_type is None


def idempotency_key(ticket: Ticket, taxonomy_version: str) -> str:
    """Same ticket content + same taxonomy version = same key.

    Webhook redeliveries and repeated backfill runs become no-ops, while an
    edited ticket or a new taxonomy version legitimately gets a fresh run.
    """
    material = "\x1f".join([ticket.key, ticket.summary, ticket.description, taxonomy_version])
    return hashlib.sha256(material.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# 2. Prompting (deliberately minimal; written for this demo)
# --------------------------------------------------------------------------

def build_prompt(stage: str, ticket: Ticket, taxonomy: dict, area: Optional[str] = None) -> str:
    options = taxonomy["problem_areas"] if stage == "area" else taxonomy["problem_types"]
    field_name = "problem_area" if stage == "area" else "problem_type"
    lines = [f"- {o['name']}: {o['description']}" for o in options]
    context = f"\nThe problem area has already been determined as: {area}" if area else ""
    return (
        f"Classify this bug report. Choose exactly one {field_name} from the list.{context}\n\n"
        + "\n".join(lines)
        + f"\n\nSummary: {ticket.summary}\nDescription: {ticket.description}\n\n"
        + f'Reply with JSON only: {{"{field_name}": "...", "confidence": 0.0-1.0, "reasoning": "..."}}'
    )


# --------------------------------------------------------------------------
# 3. Validation of model output
# --------------------------------------------------------------------------

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_and_validate(raw: str, field_name: str, allowed: set) -> StageResult:
    """Reject anything that is not exactly the contract. Never 'repair' values."""
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidModelOutput(f"not valid JSON ({exc.msg})")

    if not isinstance(data, dict):
        raise InvalidModelOutput("top-level value is not an object")

    missing = {field_name, "confidence", "reasoning"} - data.keys()
    if missing:
        raise InvalidModelOutput(f"missing keys: {sorted(missing)}")

    value = data[field_name]
    if value not in allowed:
        raise InvalidModelOutput(f"{value!r} is not in the taxonomy")

    conf = data["confidence"]
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        raise InvalidModelOutput(f"confidence {conf!r} is not a number")
    if not 0.0 <= conf <= 1.0:
        raise InvalidModelOutput(f"confidence {conf} is outside 0..1")

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise InvalidModelOutput("reasoning is empty")

    return StageResult(value=value, confidence=float(conf), reasoning=reasoning.strip(), attempts=0)


def run_stage(llm, stage: str, ticket: Ticket, taxonomy: dict, area: Optional[str] = None) -> StageResult:
    field_name = "problem_area" if stage == "area" else "problem_type"
    options = taxonomy["problem_areas"] if stage == "area" else taxonomy["problem_types"]
    allowed = {o["name"] for o in options}
    prompt = build_prompt(stage, ticket, taxonomy, area)

    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = llm.complete(ticket.key, stage, prompt)
        try:
            result = parse_and_validate(raw, field_name, allowed)
            result.attempts = attempt
            return result
        except InvalidModelOutput as exc:
            last_error = str(exc)
    return StageResult(value=None, confidence=None, reasoning="", attempts=MAX_ATTEMPTS, error=last_error)


# --------------------------------------------------------------------------
# 4. Decision
# --------------------------------------------------------------------------

AUTO_APPLY, NEEDS_REVIEW, NOT_CLASSIFIED = "auto_apply", "needs_review", "not_classified"


def decide(area: StageResult, ptype: Optional[StageResult]) -> str:
    if not area.ok or ptype is None or not ptype.ok:
        return NOT_CLASSIFIED
    if area.value in FALLBACK_VALUES or ptype.value in FALLBACK_VALUES:
        return NEEDS_REVIEW
    lowest = min(area.confidence, ptype.confidence)
    if lowest >= APPLY_AT:
        return AUTO_APPLY
    if lowest >= REVIEW_AT:
        return NEEDS_REVIEW
    return NOT_CLASSIFIED


# --------------------------------------------------------------------------
# 5. Apply + explain + audit
# --------------------------------------------------------------------------

def explain(outcome: str, area: StageResult, ptype: Optional[StageResult]) -> str:
    """Every outcome gets a visible note, including confident auto-applies.

    Commenting only on low-confidence results means the confident-but-wrong
    answers are the silent ones, and those are the ones a reviewer needs to see.
    """
    def line(name, r):
        if r is None:
            return f"{name}: not attempted"
        if not r.ok:
            return f"{name}: invalid model output after {r.attempts} attempts ({r.error})"
        return f"{name}: {r.value} (confidence {r.confidence:.2f}) - {r.reasoning}"

    head = {
        AUTO_APPLY: "Classified automatically. Correct the fields if this looks wrong.",
        NEEDS_REVIEW: "Suggested classification below. Fields were NOT changed; please confirm or correct.",
        NOT_CLASSIFIED: "Could not classify with enough certainty. Adding reproduction detail usually helps.",
    }[outcome]
    return "\n".join([head, line("Area", area), line("Type", ptype)])


def process_ticket(ticket: Ticket, llm, taxonomy: dict, audit: "AuditLog") -> str:
    if not is_eligible(ticket):
        return "skipped_human_classified"

    key = idempotency_key(ticket, taxonomy["version"])
    if audit.seen(key):
        return "skipped_already_processed"

    area = run_stage(llm, "area", ticket, taxonomy)
    ptype = run_stage(llm, "type", ticket, taxonomy, area=area.value) if area.ok else None
    outcome = decide(area, ptype)

    written = {}
    if outcome == AUTO_APPLY:  # the write gate: only this outcome touches fields
        ticket.problem_area, ticket.problem_type = area.value, ptype.value
        written = {"problem_area": area.value, "problem_type": ptype.value}
    ticket.labels.append(f"ai-{outcome.replace('_', '-')}")
    ticket.comments.append(explain(outcome, area, ptype))

    audit.append({
        "idempotency_key": key,
        "ticket": ticket.key,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": getattr(llm, "model_name", "unknown"),
        "taxonomy_version": taxonomy["version"],
        "area": vars(area),
        "type": vars(ptype) if ptype else None,
        "outcome": outcome,
        "fields_written": written,
    })
    return outcome


class AuditLog:
    """Append-only JSON Lines file. One record per processed ticket."""

    def __init__(self, path: Path):
        self.path = path
        self._keys = set()
        if path.exists():
            for raw in path.read_text().splitlines():
                if raw.strip():
                    self._keys.add(json.loads(raw)["idempotency_key"])

    def seen(self, key: str) -> bool:
        return key in self._keys

    def append(self, record: Dict) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        self._keys.add(record["idempotency_key"])


# --------------------------------------------------------------------------

def load_tickets(path: Path) -> List[Ticket]:
    data = json.loads(path.read_text())
    return [
        Ticket(
            key=t["key"], summary=t["summary"], description=t["description"],
            problem_area=t.get("problem_area"), problem_type=t.get("problem_type"),
        )
        for t in data["tickets"]
    ]


def main(argv: List[str]) -> None:
    audit_path = HERE / "out" / "audit.jsonl"
    audit_path.parent.mkdir(exist_ok=True)
    if "--reset" in argv and audit_path.exists():
        audit_path.unlink()

    taxonomy = json.loads((HERE / "taxonomy.json").read_text())
    tickets = load_tickets(HERE / "bugs.json")
    llm, audit = ScriptedLLM(), AuditLog(audit_path)

    print(f"Taxonomy {taxonomy['version']}  |  apply >= {APPLY_AT}  review >= {REVIEW_AT}\n")
    print(f"{'Ticket':<10} {'Outcome':<27} {'Area':<18} {'Type'}")
    print("-" * 78)
    for t in tickets:
        outcome = process_ticket(t, llm, taxonomy, audit)
        print(f"{t.key:<10} {outcome:<27} {str(t.problem_area):<18} {t.problem_type}")
    print(f"\nModel calls this run: {len(llm.calls)}   Audit log: {audit_path.relative_to(HERE)}")


if __name__ == "__main__":
    main(sys.argv[1:])
