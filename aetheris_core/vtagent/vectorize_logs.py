# vectorize_logs.py

import os
import json
import pickle
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Configuration ---
LOG_DIR = "synthetic_data"
OUTPUT_DIR = "faiss/logs"
LOG_FILES = [
    "siem_logs",
    "xdr_logs",
    "ids_logs",
    "firewall_logs",
    "edr_logs",
    "hids_logs",
    "application_logs",
]

# --- Utilities ---
def flatten_log(log: dict) -> str:
    """Flatten a log dictionary into a single string for vectorization."""
    parts = []
    for key, value in log.items():
        if isinstance(value, (dict, list)):
            parts.append(f"{key}: {' | '.join(map(str, value))}")
        else:
            parts.append(f"{key}: {value}")
    return " | ".join(parts)

# --- Main Vectorization Logic ---
def vectorize_log_file(log_type):
    vectorizer = TfidfVectorizer(max_features=2048)

    with open(os.path.join(LOG_DIR, f"{log_type}.json"), "r") as f:
        logs = json.load(f)

    flattened = [flatten_log(log) for log in logs]
    id_map = [f"{log_type.upper()}:{i}" for i in range(len(flattened))]

    X = vectorizer.fit_transform(flattened)
    index = faiss.IndexFlatL2(X.shape[1])
    index.add(X.toarray())

    # --- Save to Disk ---
    faiss.write_index(index, os.path.join(OUTPUT_DIR, f"{log_type}.index.index"))
    with open(os.path.join(OUTPUT_DIR, f"{log_type}.id_map.pkl"), "wb") as f:
        pickle.dump(id_map, f)
    with open(os.path.join(OUTPUT_DIR, f"{log_type}.vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)
    with open(os.path.join(OUTPUT_DIR, f"{log_type}.texts.pkl"), "wb") as f:
        pickle.dump(flattened, f)

    print(f"[✓] Vectorized {len(flattened)} {log_type.upper()} records")




# --- Run All ---
if __name__ == "__main__":
    for log_file in LOG_FILES:
        try:
            vectorize_log_file(log_file)
        except Exception as e:
            print(f"[✗] Failed to vectorize {log_file}: {str(e)}")
