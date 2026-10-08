from typing import List, Dict, Any, Optional
from app.rag.indexer import VectorIndex
from app.ingest.loaders import DataLoader

class RAGRetriever:
    """
    RAG Retriever enforcing mandatory runbook section citations and past incident similarity scoring.
    """
    def __init__(self, index: Optional[VectorIndex] = None):
        if index is None:
            loader = DataLoader()
            self.index = VectorIndex()
            self.index.build_indexes(loader)
        else:
            self.index = index

    def get_next_checks(self, alarm_name: str, alarm_code: str, node_type: str = "") -> List[Dict[str, str]]:
        """
        Retrieves cited next checks for an alarm. Every check MUST cite runbook_name + section_heading.
        """
        query = f"{alarm_name} {alarm_code} {node_type}"
        matched = self.index.search_runbooks(query=query, top_k=3, node_type=node_type)
        
        if not matched:
            return [{"check": "not found", "citation": "not found"}]
            
        checks = []
        for item in matched:
            doc = item["doc"]
            citation = item["citation"]
            content = doc["content"]
            
            checks.append({
                "runbook_name": doc["runbook_name"],
                "section_heading": doc["section_heading"],
                "citation": f"{doc['runbook_name']}#{doc['section_heading']}",
                "content": content,
                "similarity": round(item["similarity"], 3)
            })
            
        return checks

    def get_similar_incidents(self, incident_summary_query: str) -> List[Dict[str, Any]]:
        """
        Retrieves similar past incidents with similarity scores.
        """
        results = self.index.search_past_incidents(query=incident_summary_query, top_k=2)
        if not results:
            return [{"id": "not found", "similarity": 0.0, "summary": "not found"}]
        return results
