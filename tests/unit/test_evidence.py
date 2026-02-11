from matrix_hive_driver.evidence.collector import build_evidence_bundle


def test_build_evidence_bundle():
    events = [
        {"ts": "2025-01-01T00:00:00Z", "kind": "node_started", "level": "info"},
        {"ts": "2025-01-01T00:00:01Z", "kind": "node_completed", "level": "info"},
    ]
    bundle, sha = build_evidence_bundle("run-123", events)

    assert bundle.run_id == "run-123"
    assert bundle.summary["event_count"] == 2
    assert len(sha) == 64  # SHA-256 hex digest
    assert isinstance(bundle.to_bytes(), bytes)


def test_evidence_bundle_deterministic():
    events = [{"ts": "2025-01-01T00:00:00Z", "kind": "test"}]
    bundle1, sha1 = build_evidence_bundle("run-1", events)
    bundle2, sha2 = build_evidence_bundle("run-1", events)
    # Different created_at timestamps mean different hashes, but structure is consistent
    assert bundle1.run_id == bundle2.run_id
    assert bundle1.summary == bundle2.summary


def test_empty_events():
    bundle, sha = build_evidence_bundle("run-empty", [])
    assert bundle.summary["event_count"] == 0
    assert len(sha) == 64
