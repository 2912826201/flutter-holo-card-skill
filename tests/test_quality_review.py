import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/build-flutter-holo-card/scripts"))
from quality_review import PROFILES, assess, record, verify


def card(kind, score, attempts=1):
    return {"scores": {key: score for key in PROFILES[kind][1]}, "blockers": [],
            "notes": "Inspected at target display size.", "attempts": attempts}


class QualityTests(unittest.TestCase):
    def test_each_asset_accepts_exact_threshold_without_retry(self):
        for kind, (threshold, _) in PROFILES.items():
            result = assess({kind: card(kind, threshold)}, (kind,))
            self.assertTrue(result["accepted"])
            self.assertEqual(result["assets"][kind]["next_action"], "reuse")

    def test_eighty_passes_background_and_sketch_but_not_foreground(self):
        for kind, expected in (("background", True), ("lineart", True), ("foreground", False)):
            self.assertEqual(assess({kind: card(kind, 80)}, (kind,))["accepted"], expected)

    def test_high_average_does_not_hide_failed_required_asset(self):
        cards = {"foreground": card("foreground", 84), "background": card("background", 100)}
        self.assertFalse(assess(cards, cards)["accepted"])
        with self.assertRaises(ValueError):
            record(cards, cards, "pass")

    def test_blocker_overrides_score_and_two_attempts_stop(self):
        candidate = card("foreground", 99, 2)
        candidate["blockers"] = ["Main hand is missing at normal display size"]
        result = assess({"foreground": candidate}, ("foreground",))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["assets"]["foreground"]["next_action"], "stop")

    def test_first_failure_gets_only_one_edit(self):
        result = assess({"lineart": card("lineart", 65)}, ("lineart",))
        self.assertEqual(result["assets"]["lineart"]["next_action"], "edit_once")
        with self.assertRaises(ValueError):
            assess({"lineart": card("lineart", 65, 3)}, ("lineart",))

    def test_rounding_never_promotes_below_threshold(self):
        self.assertFalse(assess({"lineart": card("lineart", 74.999)}, ("lineart",))["accepted"])

    def test_invalid_scores_and_missing_assets_are_rejected(self):
        for score in (float("nan"), float("inf"), 101, -1, True, "90"):
            with self.assertRaises(ValueError):
                assess({"lineart": card("lineart", score)}, ("lineart",))
        with self.assertRaises(ValueError):
            assess({}, ("foreground",))

    def test_forged_summary_cannot_override_failed_score(self):
        quality = record({"lineart": card("lineart", 80)}, ("lineart",), "pass")
        modified = copy.deepcopy(quality)
        modified["cards"]["lineart"]["scores"]["placement"] = 10
        with self.assertRaises(ValueError):
            verify(modified, ("lineart",))
