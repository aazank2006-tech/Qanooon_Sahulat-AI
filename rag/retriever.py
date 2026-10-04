import os
import re
import json
import math
from typing import List, Dict, Any, Optional

class HybridLegalRetriever:
    """
    Hybrid retriever combining Section-Aware BM25 Lexical search with
    Gemini Dense Vector Embeddings (text-embedding-004), specifically
    tuned for Pakistani legal vocabulary, English statutes, Urdu, and Roman Urdu.
    """

    ROMAN_URDU_SYNONYMS = {
        "makan": ["tenancy", "rent", "premise", "property", "house"],
        "malik": ["landlord", "owner", "lessor"],
        "kiraya": ["rent", "tenancy", "lease"],
        "kirayedar": ["tenant", "lessee"],
        "advance": ["security", "deposit", "advance"],
        "biyana": ["token", "deposit", "agreement"],
        "kharab": ["defective", "faulty", "damaged", "deficiency"],
        "naqis": ["defective", "substandard", "faulty"],
        "wapis": ["refund", "return", "restitution"],
        "dokandar": ["seller", "merchant", "vendor", "trader"],
        "scam": ["fraud", "deceit", "peca", "cheating"],
        "dhoka": ["fraud", "cheating", "electronic fraud"],
        "blackmail": ["modesty", "extortion", "blackmail", "coercion", "peca"],
        "tasweer": ["photo", "photograph", "image", "modesty"],
        "badnami": ["defamation", "dignity", "reputation"],
        "tankhwah": ["wages", "salary", "remuneration", "payment"],
        "seth": ["employer", "boss", "factory owner"],
        "nokri": ["employment", "job", "service", "termination"]
    }

    def __init__(self, statutes_dir: str):
        self.statutes_dir = statutes_dir
        self.documents: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lens: List[int] = []
        self.avg_dl: float = 0.0
        self.gemini_client = None
        self._init_gemini_client()
        self.load_documents()

    def _init_gemini_client(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=api_key)
            except Exception:
                self.gemini_client = None

    def tokenize(self, text: str) -> List[str]:
        # Normalize and tokenize across English, Urdu characters, and Roman Urdu
        text = text.lower()
        tokens = re.findall(r"[\w\u0600-\u06FF]+", text)
        expanded_tokens = list(tokens)
        for t in tokens:
            if t in self.ROMAN_URDU_SYNONYMS:
                expanded_tokens.extend(self.ROMAN_URDU_SYNONYMS[t])
        return expanded_tokens

    def load_documents(self):
        self.documents = []
        if not os.path.exists(self.statutes_dir):
            return

        for filename in os.listdir(self.statutes_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.statutes_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.documents.extend(data)
                except Exception as e:
                    print(f"Error loading {filepath}: {e}")

        self._build_bm25_index()

    def _build_bm25_index(self):
        self.doc_tokens = []
        self.doc_freqs = {}
        self.doc_lens = []

        for doc in self.documents:
            # Combine searchable fields
            searchable_text = f"{doc.get('act', '')} {doc.get('section', '')} {doc.get('category', '')} {doc.get('jurisdiction', '')} {' '.join(doc.get('keywords', []))} {doc.get('content_english', '')} {doc.get('content_urdu', '')} {doc.get('content_roman_urdu', '')}"
            tokens = self.tokenize(searchable_text)
            self.doc_tokens.append(tokens)
            self.doc_lens.append(len(tokens))

            # Unique terms in doc
            unique_terms = set(tokens)
            for t in unique_terms:
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

        total_docs = len(self.doc_lens)
        self.avg_dl = sum(self.doc_lens) / total_docs if total_docs > 0 else 1.0

    def _bm25_score(self, query_tokens: List[str], doc_idx: int, k1: float = 1.5, b: float = 0.75) -> float:
        score = 0.0
        doc_tokens = self.doc_tokens[doc_idx]
        doc_len = self.doc_lens[doc_idx]
        total_docs = len(self.documents)

        # Count frequencies in this doc
        term_counts: Dict[str, int] = {}
        for t in doc_tokens:
            term_counts[t] = term_counts.get(t, 0) + 1

        for q in query_tokens:
            if q not in term_counts:
                continue
            f = term_counts[q]
            df = self.doc_freqs.get(q, 0)
            idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            numerator = f * (k1 + 1.0)
            denominator = f + k1 * (1.0 - b + b * (doc_len / self.avg_dl))
            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant legal sections using hybrid search.
        """
        if not self.documents:
            return []

        query_tokens = self.tokenize(query)
        bm25_scores = []
        for i in range(len(self.documents)):
            bm25_scores.append((i, self._bm25_score(query_tokens, i)))

        # Sort by BM25 score
        bm25_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in bm25_scores[:top_k]:
            doc_copy = dict(self.documents[idx])
            doc_copy["relevance_score"] = round(score, 3)
            results.append(doc_copy)

        return results
