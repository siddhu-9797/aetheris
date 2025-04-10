import os
import pickle
import numpy as np
import django
from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from vtagent.models import RawArticle
from django.conf import settings

# --- Load vectorizer ---
vectorizer_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_vectorizer.pkl")
with open(vectorizer_path, "rb") as f:
    vectorizer: TfidfVectorizer = pickle.load(f)

# --- Load article contents ---
raw_articles = RawArticle.objects.all()
contents = [article.content for article in raw_articles]

if not contents:
    print("[!] No content found in RawArticle.")
    exit()

# --- Vectorize and Save ---
X = vectorizer.transform(contents)
output_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_vectorized_articles.npz")
save_npz(output_path, X)

print(f"[✓] Vectorized matrix saved to {output_path}")
