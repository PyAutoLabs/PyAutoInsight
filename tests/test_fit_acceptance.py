"""B3 acceptance on the committed ``fit`` capture (autofit_inference#6, review 06
finding 6): schema validity alone passed on a zero-record B2 capture, so the pilot's
presence is checked explicitly.

The wave-1 pilot is 223 rows, every one flagged ``pilot``; later waves add non-pilot
rows but never remove pilot ones. For the producer revisions whose content is known
(below) the exact acceptance counts are pinned too.
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_RECORDS = 223
#: The B3 pilot (autofit_inference 900648b) carries producer revision 0c87bf1; the B3c
#: post-merge fixes (autofit_inference#6) re-export the same rows at 162644e.
KNOWN_REVISIONS = {
    "0c87bf1add74ebec24c0dda6cd6684d1c8005f95": {
        "accepted": 35,
        "rejected": 110,
        "not_assessed": 78,
    },
    "162644e5c41a507e68914cd34e6fcc42d2c5ed03": {
        "accepted": 35,
        "rejected": 110,
        "not_assessed": 78,
    },
}
#: The first producer commit whose capture holds the pilot.
FIRST_PILOT_COMMIT = "900648b5c66514167dd79a4859aed400fcc9551e"
#: Producer commits known to predate the pilot (the B2 capture had zero records).
PRE_PILOT_COMMITS = {"ec35be493712"}


def _load(kind):
    return json.loads((ROOT / kind / "fit.json").read_text())


def test_fit_capture_holds_the_wave1_pilot():
    snap, receipt = _load("snapshots"), _load("receipts")
    doc = snap["summary"]
    assert receipt["outcome"] == "ok"
    assert receipt["resolved_commit"] == snap["commit"]
    assert not any(snap["commit"].startswith(c) for c in PRE_PILOT_COMMITS)
    assert receipt["record_count"] == len(doc["records"])
    pilot = [r for r in doc["records"] if r["configuration"].get("pilot") is True]
    assert len(pilot) == PILOT_RECORDS, "the fit capture lost or never had the B3 pilot"
    assert doc["coverage"]["observed"]["records"] >= PILOT_RECORDS


def test_fit_capture_counts_match_the_known_producer_revision():
    doc = _load("snapshots")["summary"]
    expected = KNOWN_REVISIONS.get(doc["producer_revision"])
    if expected is None:
        # A later producer revision: only the pilot-presence invariant above applies.
        return
    got = Counter(r["scientific"]["acceptance"] for r in doc["records"])
    assert dict(got) == expected
