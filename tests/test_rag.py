import pytest
from app.rag.retriever import RAGRetriever

def test_rag_runbook_retrieval_and_citation():
    retriever = RAGRetriever()
    
    # Query for transport link down
    checks = retriever.get_next_checks(alarm_name="Physical Fiber Link Down", alarm_code="LINK_DOWN", node_type="Transport")
    assert len(checks) > 0
    assert checks[0]["citation"] != "not found"
    assert "RB-01_Transport_Link_Down.md" in checks[0]["citation"]
    assert "Next Checks" in checks[0]["citation"] or "Overview" in checks[0]["citation"]

def test_rag_past_incidents_retrieval():
    retriever = RAGRetriever()
    
    similar = retriever.get_similar_incidents("Transport Link Down on LINK-A causing BGP peer down on CMG-02")
    assert len(similar) > 0
    assert similar[0]["id"] != "not found"
    assert similar[0]["similarity"] > 0.3
    assert "INC-2025-0101" in similar[0]["id"] or "INC-2025" in similar[0]["id"]

def test_rag_fallback_not_found():
    retriever = RAGRetriever()
    # Query for non-existent nonsense
    checks = retriever.get_next_checks(alarm_name="xyz_unknown_quantum_flapping", alarm_code="XYZ_9999", node_type="Unknown")
    # Should either return low similarity or handle gracefully
    assert len(checks) > 0
