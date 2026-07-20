from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CSI_CAMPAIGN = REPO_ROOT / "fixtures/replay/rf-sensing/csi-link-campaign.json"
PASSIVE_CAMPAIGN = REPO_ROOT / "fixtures/replay/rf-sensing/passive-rf-campaign.json"
MULTIMODAL_CAMPAIGN = REPO_ROOT / "fixtures/replay/rf-sensing/multimodal-campaign.json"
PASSIVE_JSONL = REPO_ROOT / "fixtures/replay/rf-sensing/passive-rf-kismet.jsonl"
RVF_BINARY = REPO_ROOT / "fixtures/replay/ruview/model-rvf-binary.rvf"
RVF_JSONL = REPO_ROOT / "fixtures/replay/ruview/model-jsonl-rvf.jsonl"
RVF_CORRUPT = REPO_ROOT / "fixtures/replay/ruview/model-corrupt.bin"
FINDING_CAMPAIGN = REPO_ROOT / "fixtures/replay/rf-sensing/offline-finding-campaign.json"
FINDING_JSONL = REPO_ROOT / "fixtures/replay/rf-sensing/offline-finding-frames.jsonl"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CsiCampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rf = load_module(
            "openbrec_rf_sensing_test", REPO_ROOT / "openbrec/rf_sensing.py"
        )
        self.campaign = load_json(CSI_CAMPAIGN)

    def test_every_generated_observation_validates_against_the_addon(self) -> None:
        outcome = self.rf.run_csi_campaign(self.campaign, repository_root=REPO_ROOT)
        self.assertEqual(
            outcome["observations_generated"],
            outcome["observations_schema_validated"],
        )
        self.assertEqual(outcome["observations_generated"], 12)

    def test_empty_room_abstains_and_never_infers_absence(self) -> None:
        outcome = self.rf.run_csi_campaign(self.campaign, repository_root=REPO_ROOT)
        empty = next(
            item for item in outcome["projection"] if item["signal_kind"] == "empty"
        )
        self.assertEqual(empty["state"], "abstained")
        self.assertTrue(empty["abstained"])
        self.assertEqual(
            empty["abstention_reasons"], ["insufficient independent evidence"]
        )
        self.assertEqual(self.rf._forbidden_claim_hits(outcome["projection"]), 0)

    def test_non_human_motion_never_corroborates_presence(self) -> None:
        outcome = self.rf.run_csi_campaign(self.campaign, repository_root=REPO_ROOT)
        ventilator = next(
            item
            for item in outcome["projection"]
            if item["signal_kind"] == "non_human_motion"
        )
        self.assertEqual(ventilator["state"], "indicator")
        self.assertLessEqual(ventilator["confidence"], 0.2)

    def test_determinism_under_case_permutations(self) -> None:
        cases = self.campaign["cases"]
        hashes = self.rf._permuted_hashes(
            cases,
            lambda rotated: self.rf.run_csi_campaign(
                {**self.campaign, "cases": rotated}, repository_root=REPO_ROOT
            ),
        )
        self.assertEqual(len(hashes), 1)


class PassiveCampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rf = load_module(
            "openbrec_rf_sensing_passive_test", REPO_ROOT / "openbrec/rf_sensing.py"
        )
        self.campaign = load_json(PASSIVE_CAMPAIGN)
        self.lines = PASSIVE_JSONL.read_text(encoding="utf-8").splitlines()

    def run_campaign(self, lines: list[str]) -> dict:
        return self.rf.run_passive_campaign(
            self.campaign, repository_root=REPO_ROOT, raw_lines=lines
        )

    def test_raw_mac_never_appears_in_output(self) -> None:
        outcome = self.run_campaign(self.lines)
        self.assertEqual(outcome["mac_leaks"], 0)
        for observation in outcome["projection"]["observations"]:
            self.assertTrue(observation["subject_ref"].startswith("hmac-sha256:"))
            self.assertNotIn("ssid", observation)
            self.assertFalse(observation["payload_retained"])

    def test_payload_fields_are_rejected_visibly(self) -> None:
        outcome = self.run_campaign(self.lines)
        rejected = outcome["projection"]["rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("non-whitelisted", rejected[0]["error"])
        self.assertEqual(outcome["records_rejected"], 1)
        self.assertEqual(outcome["observations_emitted"], 4)
        self.assertEqual(outcome["duplicates_deduplicated"], 1)

    def test_subject_ref_rotates_across_epochs_and_is_stable_within(self) -> None:
        first = self.rf.rotating_subject_ref("incident-a", "epoch-1", "subject-x")
        again = self.rf.rotating_subject_ref("incident-a", "epoch-1", "subject-x")
        rotated = self.rf.rotating_subject_ref("incident-a", "epoch-2", "subject-x")
        other_incident = self.rf.rotating_subject_ref(
            "incident-b", "epoch-1", "subject-x"
        )
        self.assertEqual(first, again)
        self.assertNotEqual(first, rotated)
        self.assertNotEqual(first, other_incident)

    def test_determinism_under_input_permutations(self) -> None:
        hashes = self.rf._permuted_hashes(self.lines, self.run_campaign)
        self.assertEqual(len(hashes), 1)


class MultimodalCampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rf = load_module(
            "openbrec_rf_sensing_mm_test", REPO_ROOT / "openbrec/rf_sensing.py"
        )
        self.campaign = load_json(MULTIMODAL_CAMPAIGN)
        self.outcome = self.rf.run_multimodal_campaign(
            self.campaign, repository_root=REPO_ROOT
        )
        self.by_case = {
            item["case_id"]: item for item in self.outcome["projection"]
        }

    def test_corroboration_requires_two_independent_modalities(self) -> None:
        self.assertEqual(self.by_case["all-modalities"]["confidence"], 0.5)
        self.assertEqual(self.by_case["two-csi-links"]["confidence"], 0.2)

    def test_silence_of_one_modality_does_not_cancel_another(self) -> None:
        silent = self.by_case["csi-silent"]
        self.assertEqual(silent["state"], "indicator")
        self.assertEqual(silent["confidence"], 0.2)
        self.assertEqual(silent["usable_sources"], ["beacon-ac-1"])

    def test_insufficient_evidence_abstains(self) -> None:
        insufficient = self.by_case["insufficient-evidence"]
        self.assertEqual(insufficient["state"], "abstained")
        self.assertTrue(insufficient["abstained"])
        self.assertEqual(self.rf._forbidden_claim_hits(self.outcome["projection"]), 0)

    def test_determinism_under_case_permutations(self) -> None:
        cases = self.campaign["cases"]
        hashes = self.rf._permuted_hashes(
            cases,
            lambda rotated: self.rf.run_multimodal_campaign(
                {**self.campaign, "cases": rotated}, repository_root=REPO_ROOT
            ),
        )
        self.assertEqual(len(hashes), 1)


class OfflineFindingCampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rf = load_module(
            "openbrec_rf_sensing_finding_test", REPO_ROOT / "openbrec/rf_sensing.py"
        )
        self.campaign = load_json(FINDING_CAMPAIGN)
        self.lines = FINDING_JSONL.read_text(encoding="utf-8").splitlines()
        self.outcome = self.rf.run_offline_finding_campaign(
            self.campaign, repository_root=REPO_ROOT, raw_lines=self.lines
        )
        self.by_case = {item["case_id"]: item for item in self.outcome["projection"]}

    def test_emitted_observations_validate_and_reconcile(self) -> None:
        self.assertEqual(self.outcome["observations_emitted"], 8)
        self.assertEqual(self.outcome["records_rejected"], 2)
        self.assertEqual(self.outcome["fleet_excluded"], 1)
        self.assertEqual(self.outcome["core_observations_validated"], 11)

    def test_finding_alone_never_exceeds_weak_hint_confidence(self) -> None:
        for case_id in ("apple-find-my", "google-find-hub", "separated-airtag-rhythm"):
            case = self.by_case[case_id]
            self.assertEqual(case["state"], "indicator")
            self.assertLessEqual(case["confidence"], 0.2)
            self.assertFalse(case["abstained"])

    def test_finding_never_elevates_a_companion(self) -> None:
        case = self.by_case["finding-beside-csi"]
        self.assertEqual(case["confidence"], 0.2)
        self.assertFalse(case["finding_in_corroboration_pool"])
        self.assertEqual(len(case["weak_hint_ids"]), 1)

    def test_quiet_window_abstains_and_never_infers_absence(self) -> None:
        quiet = self.by_case["quiet-window"]
        self.assertEqual(quiet["frames_observed"], 0)
        self.assertEqual(quiet["state"], "abstained")
        self.assertEqual(
            quiet["abstention_reasons"], ["insufficient independent evidence"]
        )
        self.assertEqual(self.rf._forbidden_claim_hits(self.outcome["projection"]), 0)

    def test_own_fleet_device_is_excluded_visibly(self) -> None:
        fleet_case = self.by_case["own-fleet-device"]
        self.assertEqual(fleet_case["observations_emitted"], 0)
        self.assertEqual(fleet_case["state"], "abstained")
        self.assertEqual(self.outcome["fleet_excluded"], 1)
        self.assertEqual(self.outcome["raw_identifier_leaks"], 0)

    def test_hypothesis_stays_hypothesis_never_fact(self) -> None:
        rhythm = self.by_case["separated-airtag-rhythm"]
        self.assertEqual(rhythm["hypothesis_labels"], ["separated_airtag_rhythm"])
        self.assertNotIn("separated_airtag", rhythm["explanation"])
        findings = rhythm["finding_observations"]
        self.assertTrue(findings)
        for observation in findings:
            hypothesis = observation["classification_hypothesis"]
            self.assertEqual(hypothesis["statement_kind"], "hypothesis")
            self.assertFalse(observation["alert_trigger_allowed"])
            self.assertEqual(observation["fusion_weight"], "low")

    def test_active_or_raw_records_are_rejected_visibly(self) -> None:
        rejected = self.outcome["rejected"]
        self.assertEqual(len(rejected), 2)
        messages = " ".join(item["error"] for item in rejected)
        self.assertIn("gatt_attempt", messages)
        self.assertIn("raw_eid", messages)
        self.assertNotIn("4f:3a:9c:11:02:77", messages)
        self.assertEqual(self.outcome["schema_rejections_confirmed"], 2)

    def test_determinism_under_input_permutations(self) -> None:
        hashes = self.rf._permuted_hashes(
            self.lines,
            lambda lines: self.rf.run_offline_finding_campaign(
                self.campaign, repository_root=REPO_ROOT, raw_lines=lines
            ),
        )
        self.assertEqual(len(hashes), 1)


class RuviewModelFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ruview = load_module(
            "openbrec_ruview_test", REPO_ROOT / "openbrec/ruview.py"
        )

    def test_binary_magic_is_accepted(self) -> None:
        verdict = self.ruview.inspect_model_format(RVF_BINARY.read_bytes())
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["format"], "rvf-binary")
        self.assertEqual(len(verdict["model_sha256"]), 64)

    def test_jsonl_model_fails_with_typed_visible_error_and_fallback(self) -> None:
        with self.assertRaises(self.ruview.RvModelFormatError) as caught:
            self.ruview.inspect_model_format(RVF_JSONL.read_bytes())
        message = str(caught.exception)
        self.assertIn("invalid magic", message)
        self.assertIn("fallback:", message)
        self.assertIn("silent null", message)

    def test_unknown_magic_fails_closed_and_never_returns_null(self) -> None:
        for raw in (RVF_CORRUPT.read_bytes(), b"", b"\x00\x01\x02\x03"):
            with self.assertRaises(self.ruview.RvModelFormatError):
                self.ruview.inspect_model_format(raw)


class RfSensingGateCliTests(unittest.TestCase):
    def run_verify(self, gate: str) -> dict:
        result = subprocess.run(
            [sys.executable, "-m", "openbrec.verify", gate],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_rf_sensing_gates_pass_with_frozen_hashes(self) -> None:
        for gate in (
            "rf-sensing-csi",
            "rf-sensing-passive",
            "rf-sensing-multimodal",
            "rf-sensing-offline-finding",
        ):
            outcome = self.run_verify(gate)
            self.assertEqual(outcome["result"], "passed")
            self.assertEqual(
                outcome["summary"]["determinism_distinct_hashes"], 1
            )
            self.assertEqual(outcome["summary"]["forbidden_claim_tokens"], 0)

    def test_ruview_model_format_gate_passes(self) -> None:
        outcome = self.run_verify("ruview-model-format")
        self.assertEqual(outcome["result"], "passed")
        self.assertEqual(outcome["summary"]["accepted"], 1)
        self.assertEqual(outcome["summary"]["rejected"], 2)
        self.assertEqual(outcome["summary"]["silent_null_returns"], 0)

    def test_gates_are_registered_with_responsible_roles(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "openbrec.verify", "--help"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        for gate in (
            "rf-sensing-csi",
            "rf-sensing-passive",
            "rf-sensing-multimodal",
            "rf-sensing-offline-finding",
            "ruview-model-format",
        ):
            self.assertIn(gate, result.stdout)


if __name__ == "__main__":
    unittest.main()
