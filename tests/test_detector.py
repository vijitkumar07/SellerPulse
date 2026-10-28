
from pathlib import Path
import json

from backend.app.database import SessionLocal
from backend.app.detector import detect_anomalies


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "ground_truth.json"

EXPECTED_SCENARIOS = {
    "suspended_seller_listing_active",
    "payout_before_delivery_or_hold_release",
    "commission_applied_twice",
    "dispute_not_deducted",
    "payout_total_mismatch",
}


def get_findings():
    db = SessionLocal()
    try:
        return detect_anomalies(db)
    finally:
        db.close()


def test_all_five_anomaly_scenarios_match_ground_truth():
    assert GROUND_TRUTH_PATH.exists(), (
        "Ground truth file missing. Generate the synthetic dataset first."
    )

    ground_truth = json.loads(
        GROUND_TRUTH_PATH.read_text(encoding="utf-8")
    )

    findings = get_findings()
    detected = {}

    for finding in findings:
        detected.setdefault(finding["scenario"], []).append(
            finding["record_id"]
        )

    expected = ground_truth["anomalies"]

    assert set(expected) == EXPECTED_SCENARIOS

    for scenario, expected_ids in expected.items():
        actual_ids = detected.get(scenario, [])
        assert sorted(actual_ids) == sorted(expected_ids), (
            f"{scenario}: expected IDs {expected_ids}, "
            f"but detected {actual_ids}"
        )


def test_detector_finds_exactly_five_seeded_anomalies():
    findings = get_findings()

    assert len(findings) == 5
    assert {item["scenario"] for item in findings} == EXPECTED_SCENARIOS


def test_findings_have_required_fields():
    for finding in get_findings():
        assert finding["scenario"]
        assert finding["record_id"] is not None
        assert finding["severity"] in {"low", "medium", "high"}
        assert finding["details"]


def test_detector_does_not_return_duplicate_findings():
    findings = get_findings()
    keys = [
        (item["scenario"], item["record_id"])
        for item in findings
    ]
    assert len(keys) == len(set(keys))
