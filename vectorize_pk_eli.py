import os
import sys
import re
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

BASE_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(BASE_DIR, "data", "pk_eli_raw")
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")

# ---------------------------------------------------------------------------
# High-Speed Hybrid Embedding Function (Gemini + Local Dense Fallback)
# ---------------------------------------------------------------------------
class PKLegalEmbeddingFunction(EmbeddingFunction):
    """
    Embedding function supporting both Google Gemini text-embedding-004
    and a zero-dependency high-speed local projection embedding.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.gemini_client = None
        if self.api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.api_key)
                print("✨ Initialized Google Gemini text-embedding-004 embedding function.")
            except Exception as e:
                print(f"Notice: Gemini embedding client init failed ({e}), using local embedding engine.")

    def _local_embed_batch(self, texts: List[str], dim: int = 384) -> List[List[float]]:
        embeddings = []
        for text in texts:
            # Hash-based semantic projection with character n-grams and word hashing
            vec = np.zeros(dim, dtype=np.float32)
            words = re.findall(r"\w+", text.lower())
            if not words:
                embeddings.append(vec.tolist())
                continue

            for word in words:
                h = hash(word)
                idx = abs(h) % dim
                sign = 1.0 if (h > 0) else -1.0
                vec[idx] += sign

            # Character 3-grams
            for i in range(len(text) - 2):
                tri = text[i:i+3].lower()
                h = hash(tri)
                idx = abs(h) % dim
                sign = 1.0 if (h > 0) else -1.0
                vec[idx] += 0.5 * sign

            # L2 normalization
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            embeddings.append(vec.tolist())
        return embeddings

    def __call__(self, input: Documents) -> Embeddings:
        if self.gemini_client:
            try:
                # Batch embed with text-embedding-004
                results = []
                # Process in batches of 32
                for i in range(0, len(input), 32):
                    batch = input[i:i+32]
                    resp = self.gemini_client.models.embed_content(
                        model="text-embedding-004",
                        contents=batch
                    )
                    for e in resp.embeddings:
                        results.append(e.values)
                return results
            except Exception as e:
                print(f"Gemini API embed call failed ({e}). Falling back to local embeddings.")

        return self._local_embed_batch(input)


# ---------------------------------------------------------------------------
# Chunking Utilities
# ---------------------------------------------------------------------------
def extract_statute_title(text: str, fallback_filename: str) -> str:
    """Extracts Act/Ordinance title from the first 500 characters of a statute text."""
    sample = text[:800].replace("\r", " ")
    # Look for capitalized titles like THE ... ACT / ORDINANCE
    match = re.search(r"((?:THE\s+)?[A-Z0-9\s,\-\(\)\.]{4,100}?(?:ACT|ORDINANCE|ORDER|REGULATION|RULES|CODE),\s*\d{4})", sample)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if len(title) > 8:
            return title
    
    # Try looking for lines with ACT / ORDINANCE
    lines = [line.strip() for line in sample.split("\n") if line.strip()]
    for line in lines[:10]:
        if any(kw in line.upper() for kw in ["ACT", "ORDINANCE", "CODE", "RULES", "ORDER"]) and len(line) < 120:
            return line

    return fallback_filename.replace(".pdf", "")

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """Splits text into overlapping chunks."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Vectorization Pipeline
# ---------------------------------------------------------------------------
class PKELIVectorizer:
    def __init__(self, chroma_dir: str = CHROMA_DIR):
        self.chroma_dir = chroma_dir
        os.makedirs(self.chroma_dir, exist_ok=True)
        print(f"📂 Persistent ChromaDB Path: {self.chroma_dir}")
        self.client = chromadb.PersistentClient(path=self.chroma_dir)
        self.embed_fn = PKLegalEmbeddingFunction()

        self.statutes_col = self.client.get_or_create_collection(
            name="pk_federal_statutes",
            embedding_function=self.embed_fn,
            metadata={"description": "967 Pakistani Federal Statutes (pk-eli corpus)"}
        )

        self.judgments_col = self.client.get_or_create_collection(
            name="pk_supreme_court_judgments",
            embedding_function=self.embed_fn,
            metadata={"description": "1,414 Supreme Court of Pakistan Judgments (pk-eli corpus)"}
        )

    def vectorize_statutes(self, json_path: str, max_statutes: Optional[int] = None, batch_size: int = 150):
        print(f"\n=======================================================")
        print(f"📖 Vectorizing Federal Statutes from: {json_path}")
        print(f"=======================================================")

        if not os.path.exists(json_path):
            print(f"❌ File not found: {json_path}")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if max_statutes:
            data = data[:max_statutes]

        total_laws = len(data)
        print(f"Loaded {total_laws:,} statutes for chunking and vector indexing.")

        batch_ids = []
        batch_docs = []
        batch_metas = []
        total_chunks = 0

        for law_idx, item in enumerate(tqdm(data, desc="Processing Statutes", ncols=80)):
            file_name = item.get("file_name", f"law_{law_idx}.pdf")
            full_text = item.get("text", "")
            title = extract_statute_title(full_text, file_name)

            chunks = chunk_text(full_text, chunk_size=1200, overlap=150)
            for c_idx, chunk in enumerate(chunks):
                chunk_id = f"statute_{law_idx}_{c_idx}"
                meta = {
                    "source_type": "statute",
                    "law_index": law_idx,
                    "title": title[:200],
                    "file_name": file_name,
                    "chunk_index": c_idx,
                    "total_chunks": len(chunks)
                }

                batch_ids.append(chunk_id)
                batch_docs.append(f"[{title}]\n{chunk}")
                batch_metas.append(meta)

                if len(batch_ids) >= batch_size:
                    self.statutes_col.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
                    total_chunks += len(batch_ids)
                    batch_ids, batch_docs, batch_metas = [], [], []

        if batch_ids:
            self.statutes_col.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            total_chunks += len(batch_ids)

        print(f"✅ Successfully indexed {total_chunks:,} statute chunks in ChromaDB ('pk_federal_statutes')!")
        print(f"📊 Current Collection Count: {self.statutes_col.count():,} vectors.")

    def vectorize_judgments(self, parquet_path: str, max_cases: Optional[int] = None, batch_size: int = 150):
        print(f"\n=======================================================")
        print(f"⚖️ Vectorizing Supreme Court Judgments from: {parquet_path}")
        print(f"=======================================================")

        if not os.path.exists(parquet_path):
            print(f"❌ File not found: {parquet_path}")
            return

        df = pd.read_parquet(parquet_path)
        if max_cases:
            df = df.head(max_cases)

        total_cases = len(df)
        print(f"Loaded {total_cases:,} Supreme Court cases. Columns: {list(df.columns)}")

        # Detect text and title column names
        text_col = "judgment" if "judgment" in df.columns else ("text" if "text" in df.columns else df.columns[1])
        title_col = "case_title" if "case_title" in df.columns else ("citation" if "citation" in df.columns else df.columns[0])

        batch_ids = []
        batch_docs = []
        batch_metas = []
        total_chunks = 0

        for row_idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing SC Judgments", ncols=80):
            raw_text = str(row.get("text", ""))

            # Extract clean citation and header
            citation = ""
            try:
                c_raw = row.get("citation_number") or row.get("case_details")
                if isinstance(c_raw, str) and "id" in c_raw:
                    import ast
                    cd = ast.literal_eval(c_raw)
                    citation = cd.get("id", "").replace(".pdf", "")
            except Exception:
                pass

            case_header = ""
            first_lines = [l.strip() for l in raw_text[:400].split("\n") if l.strip()]
            for l in first_lines:
                if any(k in l.upper() for k in ["APPEAL", "PETITION", "CRIMINAL", "CIVIL", "CONSTITUTION", "VS", "VERSUS"]):
                    case_header = l[:100]
                    break

            case_title = f"{citation} ({case_header})" if (citation and case_header) else (citation or case_header or f"Supreme Court Case {row_idx}")

            chunks = chunk_text(raw_text, chunk_size=1400, overlap=200)
            for c_idx, chunk in enumerate(chunks):
                chunk_id = f"sc_{row_idx}_{c_idx}"
                meta = {
                    "source_type": "judgment",
                    "case_index": int(row_idx),
                    "case_title": case_title[:200],
                    "citation": citation[:100],
                    "chunk_index": c_idx,
                    "total_chunks": len(chunks)
                }

                batch_ids.append(chunk_id)
                batch_docs.append(f"Supreme Court of Pakistan [{case_title}]\n{chunk}")
                batch_metas.append(meta)

                if len(batch_ids) >= batch_size:
                    self.judgments_col.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
                    total_chunks += len(batch_ids)
                    batch_ids, batch_docs, batch_metas = [], [], []

        if batch_ids:
            self.judgments_col.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            total_chunks += len(batch_ids)

        print(f"✅ Successfully indexed {total_chunks:,} judgment chunks in ChromaDB ('pk_supreme_court_judgments')!")
        print(f"📊 Current Collection Count: {self.judgments_col.count():,} vectors.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vectorize pk-eli-mcp Pakistani statutes and SC judgments into ChromaDB.")
    parser.add_argument("--statutes-limit", type=int, default=None, help="Limit number of statutes to vectorize (e.g. 50)")
    parser.add_argument("--judgments-limit", type=int, default=None, help="Limit number of judgments to vectorize (e.g. 50)")
    parser.add_argument("--batch-size", type=int, default=150, help="Batch size for ChromaDB upsert")
    args = parser.parse_args()

    statutes_json = os.path.join(RAW_DIR, "pakistan_laws_dataset.json")
    judgments_parquet = os.path.join(RAW_DIR, "supreme_court_judgments.parquet")

    vectorizer = PKELIVectorizer()
    if os.path.exists(statutes_json):
        vectorizer.vectorize_statutes(statutes_json, max_statutes=args.statutes_limit, batch_size=args.batch_size)
    if os.path.exists(judgments_parquet):
        vectorizer.vectorize_judgments(judgments_parquet, max_cases=args.judgments_limit, batch_size=args.batch_size)

