# vectorize_ad.py
import os
import sys
import django
import pickle
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
import numpy as np

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticad.models import ADUser, ADGroup, OrganizationalUnit, Domain, DomainController, ServiceAccount

# --- Vectorization Helpers ---
def get_ou_path(ou):
    parts = [ou.name]
    while ou.parent:
        ou = ou.parent
        parts.append(ou.name)
    return " > ".join(reversed(parts))

def build_text_representation():
    descriptions = []
    id_map = []

    # ADUser
    for obj in ADUser.objects.all():
        text = f"ADUser: {obj.display_name} ({obj.sAMAccountName}) - Dept: {obj.department}, Country: {obj.country}, Email: {obj.mail}"
        if obj.ou:
            text += f", OU: {obj.ou.name}"
        descriptions.append(text)
        id_map.append(f"ADUser:{obj.id}")

    # ADGroup
    for obj in ADGroup.objects.all():
        text = f"ADGroup: {obj.name} - Desc: {obj.description}"
        descriptions.append(text)
        id_map.append(f"ADGroup:{obj.id}")

    # OrganizationalUnit
    for obj in OrganizationalUnit.objects.all():
        text = f"OrganizationalUnit: {obj.name} - Path: {get_ou_path(obj)}"
        descriptions.append(text)
        id_map.append(f"OrganizationalUnit:{obj.id}")

    # Domain
    for obj in Domain.objects.all():
        text = f"Domain: {obj.name}"
        descriptions.append(text)
        id_map.append(f"Domain:{obj.id}")

    # DomainController
    for obj in DomainController.objects.all():
        text = f"DomainController: {obj.hostname} ({obj.location}) in Domain {obj.domain.name}"
        descriptions.append(text)
        id_map.append(f"DomainController:{obj.id}")
    
    # ServiceAccount
    for obj in ServiceAccount.objects.all():
        text = f"ServiceAccount: {obj.name} - Purpose: {obj.purpose}, Domain: {obj.domain.name}"
        if obj.created_for:
            text += f", Created for OU: {obj.created_for.name}"
        descriptions.append(text)
        id_map.append(f"ServiceAccount:{obj.id}")

    return descriptions, id_map

# --- Main Vectorization ---
descriptions, id_map = build_text_representation()
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(descriptions).toarray().astype("float32")

index = faiss.IndexFlatL2(X.shape[1])
index.add(X)

# --- Save files ---
output_dir = os.path.join("faiss", "ad")
os.makedirs(output_dir, exist_ok=True)

with open(os.path.join(output_dir, "id_map.pkl"), "wb") as f:
    pickle.dump(id_map, f)

with open(os.path.join(output_dir, "vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)

with open(os.path.join(output_dir, "texts.pkl"), "wb") as f:
    pickle.dump(descriptions, f)

faiss.write_index(index, os.path.join(output_dir, "index.index"))

print(f"[✓] Vectorized {len(id_map)} AD records")
print(f"[✓] FAISS index stored at: {output_dir}/index.index")
print(f"[✓] ID map stored at: {output_dir}/id_map.pkl")
print(f"[✓] Vectorizer stored at: {output_dir}/vectorizer.pkl")
print(f"[✓] Text descriptions stored at: {output_dir}/texts.pkl")