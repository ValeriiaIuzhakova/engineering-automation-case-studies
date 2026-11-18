"""
NON-PRODUCTION DEMONSTRATION. Run:  python3 -m unittest test_pipeline -v
"""

import json
import tempfile
import unittest
from pathlib import Path

import pipeline as p
from calibration import FLAT, WELL_CALIBRATED, calibration_table, is_informative
from fake_llm import ScriptedLLM

HERE = Path(__file__).parent
TAXONOMY = json.loads((HERE / "taxonomy.json").read_text())
AREAS = {a["name"] for a in TAXONOMY["problem_areas"]}


def ok(field, value, conf):
    return json.dumps({field: value, "confidence": conf, "reasoning": "r"})


class ValidationTests(unittest.TestCase):
    def test_accepts_fenced_json(self):
        r = p.parse_and_validate("```json\n" + ok("problem_area", "Search", 0.8) + "\n```", "problem_area", AREAS)
        self.assertEqual(r.value, "Search")

    def test_rejects_value_outside_taxonomy(self):
        with self.assertRaises(p.InvalidModelOutput):
            p.parse_and_validate(ok("problem_area", "Reporting", 0.9), "problem_area", AREAS)

    def test_rejects_non_numeric_and_out_of_range_confidence(self):
        for bad in ('"high"', "true", "1.4", "-0.1"):
            raw = '{"problem_area": "Search", "confidence": %s, "reasoning": "r"}' % bad
            with self.assertRaises(p.InvalidModelOutput, msg=bad):
                p.parse_and_validate(raw, "problem_area", AREAS)

    def test_rejects_missing_reasoning(self):
        with self.assertRaises(p.InvalidModelOutput):
            p.parse_and_validate('{"problem_area": "Search", "confidence": 0.9}', "problem_area", AREAS)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = p.AuditLog(Path(self.tmp.name) / "audit.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def run_one(self, script, ticket=None):
        ticket = ticket or p.Ticket("T-1", "s", "d")
        return ticket, p.process_ticket(ticket, ScriptedLLM(script), TAXONOMY, self.audit)

    def test_confident_answers_are_applied_and_still_explained(self):
        t, outcome = self.run_one({
            ("T-1", "area"): [ok("problem_area", "Search", 0.95)],
            ("T-1", "type"): [ok("problem_type", "Performance", 0.92)],
        })
        self.assertEqual(outcome, p.AUTO_APPLY)
        self.assertEqual((t.problem_area, t.problem_type), ("Search", "Performance"))
        self.assertEqual(len(t.comments), 1)  # auto-applies are not silent

    def test_mid_confidence_suggests_but_never_writes(self):
        t, outcome = self.run_one({
            ("T-1", "area"): [ok("problem_area", "Search", 0.95)],
            ("T-1", "type"): [ok("problem_type", "Performance", 0.75)],
        })
        self.assertEqual(outcome, p.NEEDS_REVIEW)
        self.assertIsNone(t.problem_area)
        self.assertIn("NOT changed", t.comments[0])

    def test_fallback_value_is_never_auto_applied(self):
        _, outcome = self.run_one({
            ("T-1", "area"): [ok("problem_area", "Other (Needs Classification)", 0.99)],
            ("T-1", "type"): [ok("problem_type", "Functional Defect", 0.99)],
        })
        self.assertEqual(outcome, p.NEEDS_REVIEW)

    def test_retry_recovers_from_one_bad_response(self):
        t, outcome = self.run_one({
            ("T-1", "area"): ["not json", ok("problem_area", "Billing", 0.93)],
            ("T-1", "type"): [ok("problem_type", "Functional Defect", 0.91)],
        })
        self.assertEqual(outcome, p.AUTO_APPLY)

    def test_persistent_bad_output_fails_closed_and_skips_stage_two(self):
        llm = ScriptedLLM({("T-1", "area"): ["nope", "still nope"]})
        t = p.Ticket("T-1", "s", "d")
        outcome = p.process_ticket(t, llm, TAXONOMY, self.audit)
        self.assertEqual(outcome, p.NOT_CLASSIFIED)
        self.assertNotIn(("T-1", "type"), llm.calls)
        self.assertIsNone(t.problem_area)

    def test_partially_human_classified_ticket_is_untouched(self):
        t = p.Ticket("T-1", "s", "d", problem_area="Billing")
        _, outcome = self.run_one({}, ticket=t)
        self.assertEqual(outcome, "skipped_human_classified")
        self.assertEqual(t.comments, [])

    def test_rerun_is_a_no_op_but_edit_or_new_taxonomy_reprocesses(self):
        script = {("T-1", "area"): [ok("problem_area", "Search", 0.95)],
                  ("T-1", "type"): [ok("problem_type", "Performance", 0.5)]}
        self.run_one(script)
        _, second = self.run_one(script)
        self.assertEqual(second, "skipped_already_processed")

        _, edited = self.run_one(script, ticket=p.Ticket("T-1", "s", "d + repro steps"))
        self.assertNotEqual(edited, "skipped_already_processed")

        newer = dict(TAXONOMY, version="v8")
        outcome = p.process_ticket(p.Ticket("T-1", "s", "d"), ScriptedLLM(script), newer, self.audit)
        self.assertNotEqual(outcome, "skipped_already_processed")


class CalibrationTests(unittest.TestCase):
    def test_flat_confidence_is_flagged(self):
        self.assertFalse(is_informative(calibration_table(FLAT)))

    def test_calibrated_confidence_passes(self):
        self.assertTrue(is_informative(calibration_table(WELL_CALIBRATED)))


if __name__ == "__main__":
    unittest.main()
