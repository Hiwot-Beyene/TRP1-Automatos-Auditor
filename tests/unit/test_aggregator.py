"""Unit tests for EvidenceAggregatorNode (contract: fan-in, normalize)."""

import pytest
from src.state import Evidence
from src.nodes.aggregator import EvidenceAggregatorNode


def test_aggregator_empty_state_returns_empty():
    assert EvidenceAggregatorNode({}) == {}
    assert EvidenceAggregatorNode({"evidences": {}}) == {}


def test_aggregator_passes_through_valid_evidences():
    e1 = Evidence(goal="g1", found=True, location="l", rationale="r", confidence=0.5)
    e2 = Evidence(goal="g2", found=False, location="l", rationale="r", confidence=0.0)
    state = {"evidences": {"dim1": [e1], "dim2": [e2]}}
    out = EvidenceAggregatorNode(state)
    assert out == {"evidences": {"dim1": [e1], "dim2": [e2]}}


def test_aggregator_filters_non_evidence_in_lists():
    e = Evidence(goal="g", found=True, location="l", rationale="r", confidence=0.0)
    state = {"evidences": {"dim1": [e, {"not": "evidence"}, None]}}
    out = EvidenceAggregatorNode(state)
    assert list(out["evidences"].keys()) == ["dim1"]
    assert len(out["evidences"]["dim1"]) == 1
    assert out["evidences"]["dim1"][0] == e


def test_aggregator_skips_non_list_values():
    state = {"evidences": {"dim1": "not a list", "dim2": []}}
    out = EvidenceAggregatorNode(state)
    assert out == {"evidences": {"dim2": []}}
