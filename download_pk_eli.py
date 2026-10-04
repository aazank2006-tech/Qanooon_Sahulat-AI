import os
import sys
import requests
import json
from tqdm import tqdm

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "pk_eli_raw")
os.makedirs(RAW_DIR, exist_ok=True)

DATASETS = {
    "statutes": {
        "url": "https://huggingface.co/datasets/AyeshaJadoon/Pakistan_Laws_Dataset/resolve/main/pdf_data.json",
        "file": os.path.join(RAW_DIR, "pakistan_laws_dataset.json"),
        "desc": "Pakistan Federal Statutes (967 laws)"
    },
    "judgments": {
        "url": "https://huggingface.co/datasets/Ibtehaj10/supreme-court-of-pak-judgments/resolve/main/data/train-00000-of-00001.parquet",
        "file": os.path.join(RAW_DIR, "supreme_court_judgments.parquet"),
        "desc": "Supreme Court Judgments (1,414 cases)"
    }
}

def download_file(url: str, dest_path: str, desc: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f"✅ {desc} already downloaded: {dest_path} ({os.path.getsize(dest_path):,} bytes)")
        return dest_path

    print(f"📥 Downloading {desc} from {url}...")
    headers = {"User-Agent": "QanoonSahulat-VectorPipeline/1.0"}
    response = requests.get(url, stream=True, headers=headers, timeout=60)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024 * 1024 # 1 MB chunks

    with open(dest_path, "wb") as f, tqdm(
        total=total_size, unit="iB", unit_scale=True, desc=desc, ncols=80
    ) as progress_bar:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                progress_bar.update(len(chunk))

    print(f"✅ Saved {desc} to {dest_path} ({os.path.getsize(dest_path):,} bytes)")
    return dest_path

if __name__ == "__main__":
    for key, info in DATASETS.items():
        download_file(info["url"], info["file"], info["desc"])
