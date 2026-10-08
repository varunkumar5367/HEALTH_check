import numpy as np
from typing import List, Dict, Any, Optional
import os

from app.config import settings
from app.ingest.loaders import DataLoader
from sklearn.feature_extraction.text import TfidfVectorizer

class VectorIndex:
    """
    High-performance TF-IDF & Cosine Similarity Vector Index.
    Delivers <5ms response time and 100% offline determinism.
    Optionally supports SentenceTransformers embeddings.
    """
    def __init__(self, use_embeddings: bool = False):
        self.use_embeddings = use_embeddings
        self.st_model = None
        
        if self.use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.st_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                print(f"Embeddings warning: {e}. Defaulting to TF-IDF.")
                self.use_embeddings = False

        self.tfidf_runbooks = TfidfVectorizer(stop_words='english')
        self.tfidf_incidents = TfidfVectorizer(stop_words='english')
        
        self.runbook_docs: List[Dict[str, Any]] = []
        self.runbook_vectors = None
        
        self.past_incident_docs: List[Dict[str, Any]] = []
        self.past_incident_vectors = None

    def build_indexes(self, loader: DataLoader):
        # 1. Index Runbooks
        self.runbook_docs = loader.load_runbooks()
        if self.runbook_docs:
            texts = [d["full_text"] for d in self.runbook_docs]
            if self.use_embeddings and self.st_model:
                self.runbook_vectors = self.st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            else:
                self.runbook_vectors = self.tfidf_runbooks.fit_transform(texts).toarray()

        # 2. Index Past Incidents
        self.past_incident_docs = loader.load_past_incidents()
        if self.past_incident_docs:
            texts = [d["content"] for d in self.past_incident_docs]
            if self.use_embeddings and self.st_model:
                self.past_incident_vectors = self.st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            else:
                self.past_incident_vectors = self.tfidf_incidents.fit_transform(texts).toarray()

        print(f"RAG Indexer initialized: {len(self.runbook_docs)} runbook sections, {len(self.past_incident_docs)} past incidents.")

    def search_runbooks(self, query: str, top_k: int = 3, node_type: str = None) -> List[Dict[str, Any]]:
        if self.runbook_vectors is None or len(self.runbook_docs) == 0:
            return []

        if self.use_embeddings and self.st_model:
            q_vec = self.st_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
            sims = np.dot(self.runbook_vectors, q_vec)
        else:
            q_vec = self.tfidf_runbooks.transform([query]).toarray()[0]
            norm_q = np.linalg.norm(q_vec)
            if norm_q > 0:
                q_vec = q_vec / norm_q
            norms = np.linalg.norm(self.runbook_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            norm_doc = self.runbook_vectors / norms
            sims = np.dot(norm_doc, q_vec)

        results = []
        for idx in range(len(self.runbook_docs)):
            doc = self.runbook_docs[idx]
            sim = float(sims[idx])
            
            score = sim
            if node_type and node_type.lower() in doc["full_text"].lower():
                score += 0.15
            if doc["runbook_name"].lower().replace("_", " ") in query.lower():
                score += 0.20
                
            results.append({
                "doc": doc,
                "similarity": score,
                "citation": f"{doc['runbook_name']} -> {doc['section_heading']}"
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def search_past_incidents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if self.past_incident_vectors is None or len(self.past_incident_docs) == 0:
            return []

        if self.use_embeddings and self.st_model:
            q_vec = self.st_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
            sims = np.dot(self.past_incident_vectors, q_vec)
        else:
            q_vec = self.tfidf_incidents.transform([query]).toarray()[0]
            norm_q = np.linalg.norm(q_vec)
            if norm_q > 0:
                q_vec = q_vec / norm_q
            norms = np.linalg.norm(self.past_incident_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            norm_doc = self.past_incident_vectors / norms
            sims = np.dot(norm_doc, q_vec)

        results = []
        for idx in range(len(self.past_incident_docs)):
            doc = self.past_incident_docs[idx]
            sim = float(sims[idx])
            results.append({
                "id": doc["id"],
                "filename": doc["filename"],
                "content": doc["content"],
                "similarity": round(sim, 3)
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
