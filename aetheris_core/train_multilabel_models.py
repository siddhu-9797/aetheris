import os
import django
import sys
import pickle
from django.conf import settings
import numpy as np
import pandas as pd
from scipy.sparse import load_npz

from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import classification_report
import joblib

# === Setup Django ===
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# === Load TF-IDF vectorized matrix ===
tfidf_matrix_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_vectorized_articles.npz")
article_ids_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_id_map.pkl")

print("[*] Loading vectorized articles...")
X = load_npz(tfidf_matrix_path)

with open(article_ids_path, "rb") as f:
    article_ids = pickle.load(f)

# === Load taxonomy labels from DB ===
print("[*] Loading taxonomy labels from DB...")
label_qs = GeneratedTaxonomyLabel.objects.filter(raw_article_id__in=article_ids)

df = pd.DataFrame([
    {
        "article_id": obj.raw_article.id,
        "platform": obj.platform,
        "software": obj.software,
        "connectivity": obj.connectivity,
        "hardware_vendor": obj.hardware_vendor,
        "network_zone": obj.network_zone,
        "country": obj.country,
        "city": obj.city,
        "business_unit": obj.business_unit,
        "department": obj.department,
        "security_posture": obj.security_posture,
        "severity": obj.severity,
        "impact": obj.impact,
        "actor": obj.actor,
        "origin": obj.origin,
        "compliance": obj.compliance,
    }
    for obj in label_qs
])

df.set_index("article_id", inplace=True)
df = df.loc[[i for i in article_ids if i in df.index]]  # Keep only aligned records

# === Prepare target variables ===
mlb_dict = {}
Y_encoded = pd.DataFrame(index=df.index)

for column in df.columns:
    mlb = MultiLabelBinarizer()
    column_data = df[column].apply(lambda x: x if isinstance(x, list) else [x] if pd.notnull(x) else [])
    Y_part = mlb.fit_transform(column_data)
    part_df = pd.DataFrame(
        Y_part,
        columns=[f"{column}__{cls}" for cls in mlb.classes_],
        index=df.index
    )
    Y_encoded = pd.concat([Y_encoded, part_df], axis=1)
    mlb_dict[column] = mlb

# === Drop all-zero label columns ===
non_zero_cols = Y_encoded.columns[(Y_encoded != 0).any(axis=0)]
Y_encoded = Y_encoded[non_zero_cols]
print(f"[INFO] Training on {len(non_zero_cols)} non-empty labels.")

# === Train/Test split ===
# === Train/Test split ===
print("[*] Splitting train/test data...")
X_train, X_test, y_train, y_test = train_test_split(X, Y_encoded, test_size=0.2, random_state=42)

# === Drop label columns with only one class in training
y_train = pd.DataFrame(y_train, columns=Y_encoded.columns)
valid_cols = [col for col in y_train.columns if len(set(y_train[col])) > 1]
y_train = y_train[valid_cols]
y_test = pd.DataFrame(y_test, columns=Y_encoded.columns)[valid_cols]

print(f"[INFO] Final label count after removing single-class labels: {len(valid_cols)}")


# === Define models with base_score
models = {
    "ML-XGBoost": MultiOutputClassifier(XGBClassifier(
        use_label_encoder=False,
        eval_metric="logloss",
        base_score=0.5  # Fix for base_score error
    )),
    "ML-LinearSVC": MultiOutputClassifier(LinearSVC()),
    "ML-LogisticRegression": MultiOutputClassifier(LogisticRegression(max_iter=200))
}


results = {}

# === Train and evaluate ===
for name, model in models.items():
    print(f"[+] Training {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
    results[name] = {
        "model": model,
        "report": report
    }
    print(f"[✓] Completed {name}.")

# === Save models and encoders ===
model_dir = os.path.join(settings.BASE_DIR, "aetheris_core", "models")
os.makedirs(model_dir, exist_ok=True)


for name, data in results.items():
    with open(os.path.join(model_dir, f"{name}_model.pkl"), "wb") as f:
        pickle.dump(data["model"], f)
    print(f"[✓] Saved {name}_model.pkl")

with open(os.path.join(model_dir, "label_encoders.pkl"), "wb") as f:
    pickle.dump(mlb_dict, f)
    
# === Save label names (column names of final training labels)
with open(os.path.join(model_dir, "label_names.pkl"), "wb") as f:
    pickle.dump(list(y_train.columns), f)
print(f"[✓] Saved label_names.pkl")



print("[✓] ML model training complete.")
