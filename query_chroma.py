import os
import sys
import chromadb
from vectorize_pk_eli import PKLegalEmbeddingFunction, CHROMA_DIR

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class PKLegalVectorStore:
    """
    Search interface over vectorized Pakistani Federal Statutes and Supreme Court Judgments.
    """
    def __init__(self, chroma_dir: str = CHROMA_DIR):
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self.embed_fn = PKLegalEmbeddingFunction()
        
        try:
            self.statutes_col = self.client.get_collection(
                name="pk_federal_statutes",
                embedding_function=self.embed_fn
            )
        except Exception:
            self.statutes_col = None

        try:
            self.judgments_col = self.client.get_collection(
                name="pk_supreme_court_judgments",
                embedding_function=self.embed_fn
            )
        except Exception:
            self.judgments_col = None

    def search_statutes(self, query: str, top_k: int = 5):
        if not self.statutes_col:
            return []
        res = self.statutes_col.query(
            query_texts=[query],
            n_results=top_k
        )
        hits = []
        if res and res["documents"]:
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                hits.append({
                    "title": meta.get("title", "Statute"),
                    "file_name": meta.get("file_name"),
                    "chunk_index": meta.get("chunk_index"),
                    "distance": round(dist, 4),
                    "text": doc
                })
        return hits

    def search_judgments(self, query: str, top_k: int = 5):
        if not self.judgments_col:
            return []
        res = self.judgments_col.query(
            query_texts=[query],
            n_results=top_k
        )
        hits = []
        if res and res["documents"]:
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                hits.append({
                    "case_title": meta.get("case_title", "Supreme Court Judgment"),
                    "case_index": meta.get("case_index"),
                    "chunk_index": meta.get("chunk_index"),
                    "distance": round(dist, 4),
                    "text": doc
                })
        return hits

    def search_all(self, query: str, top_k: int = 5):
        statutes = self.search_statutes(query, top_k=top_k)
        judgments = self.search_judgments(query, top_k=top_k)
        all_hits = statutes + judgments
        all_hits.sort(key=lambda x: x["distance"])
        return all_hits[:top_k]

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Pakistan Penal Code Section 302 murder punishment"
    print(f"🔍 Searching ChromaDB for: '{q}'\n")

    store = PKLegalVectorStore()
    results = store.search_all(q, top_k=4)

    if not results:
        print("No vectors found yet. Run vectorize_pk_eli.py after downloading to populate ChromaDB.")
    else:
        for idx, r in enumerate(results, 1):
            title = r.get("title") or r.get("case_title")
            print(f"--- [Result {idx}] (Distance: {r['distance']}) ---")
            print(f"📌 Source: {title}")
            print(f"📝 Text Snippet:\n{r['text'][:350]}...\n")

