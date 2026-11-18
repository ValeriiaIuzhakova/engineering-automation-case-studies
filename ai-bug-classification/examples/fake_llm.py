"""
NON-PRODUCTION DEMONSTRATION. Synthetic data only.

A scripted stand-in for an LLM API so the pipeline can run offline and
deterministically. Each (ticket, stage) pair returns a queue of raw strings,
including deliberately broken ones, so the validation and retry paths are
exercised the way a real model occasionally exercises them.
"""

from collections import defaultdict, deque
from typing import Dict, List, Tuple


def _ok(field: str, value: str, confidence: float, reasoning: str) -> str:
    return (
        '{"%s": "%s", "confidence": %s, "reasoning": "%s"}'
        % (field, value, confidence, reasoning)
    )


SCRIPT: Dict[Tuple[str, str], List[str]] = {
    # Clean, confident answers in both stages -> auto-apply.
    ("DEMO-101", "area"): [_ok("problem_area", "Boards & Cards", 0.95, "Card moves between columns.")],
    ("DEMO-101", "type"): [_ok("problem_type", "Regression", 0.93, "Reporter says it worked before a release.")],

    # Stage 2 first answer is prose wrapped around broken JSON; the retry is valid.
    ("DEMO-102", "area"): [_ok("problem_area", "Calendar Sync", 0.94, "Sync to an external calendar.")],
    ("DEMO-102", "type"): [
        "Sure! Here is the classification: {problem_type: Integration, confidence: 0.9",
        "```json\n" + _ok("problem_type", "Integration", 0.91, "Provider returns 403 at the boundary.") + "\n```",
    ],

    # Thin ticket -> low confidence -> nothing written, ask for detail.
    ("DEMO-103", "area"): [_ok("problem_area", "Search", 0.62, "Mentions search but no specifics.")],
    ("DEMO-103", "type"): [_ok("problem_type", "Performance", 0.55, "Says slow, but no timings or scope.")],

    # Stage 2 invents a value outside the taxonomy; retry returns a valid but
    # mid-confidence answer -> needs review.
    ("DEMO-104", "area"): [_ok("problem_area", "Import & Export", 0.92, "CSV export.")],
    ("DEMO-104", "type"): [
        _ok("problem_type", "Data Loss", 0.88, "Rows are missing."),
        _ok("problem_type", "Data Integrity", 0.78, "Rows dropped during export; could also be a functional defect."),
    ],

    # DEMO-105 is never sent: a human already classified it.

    # Stage 2 keeps returning a non-numeric confidence -> validation failure.
    ("DEMO-106", "area"): [_ok("problem_area", "Notifications", 0.90, "Duplicate email notification.")],
    ("DEMO-106", "type"): [
        '{"problem_type": "Functional Defect", "confidence": "high", "reasoning": "Sent twice."}',
        '{"problem_type": "Functional Defect", "confidence": "very high", "reasoning": "Sent twice."}',
    ],
}


class ScriptedLLM:
    model_name = "scripted-demo-model"

    def __init__(self, script: Dict[Tuple[str, str], List[str]] = None):
        source = SCRIPT if script is None else script
        self._queues = defaultdict(deque, {k: deque(v) for k, v in source.items()})
        self.calls: List[Tuple[str, str]] = []

    def complete(self, ticket_key: str, stage: str, prompt: str) -> str:
        self.calls.append((ticket_key, stage))
        queue = self._queues[(ticket_key, stage)]
        if not queue:
            return "I'm not able to help with that."
        # Repeat the last scripted answer if the caller retries more than scripted.
        return queue.popleft() if len(queue) > 1 else queue[0]
