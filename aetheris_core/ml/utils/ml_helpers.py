# ml/utils/ml_helpers.py

import joblib
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier
from sklearn.metrics import classification_report

MODEL_TYPES = {
    "random_forest": RandomForestClassifier,
    "logistic_regression": LogisticRegression,
    "linear_svc": LinearSVC,
    "xgboost": XGBClassifier
}

def train_multilabel_classifier(X, Y, model_type="random_forest", **kwargs):
    """Trains a multi-label classifier and returns the trained model."""
    base_model_class = MODEL_TYPES.get(model_type)
    if base_model_class is None:
        raise ValueError(f"Unsupported model type: {model_type}")

    base_model = base_model_class(**kwargs)
    model = MultiOutputClassifier(base_model)
    model.fit(X, Y)
    return model

def save_model(model, path):
    joblib.dump(model, path)
    print(f"[✓] Saved model to: {path}")

def load_model(path):
    return joblib.load(path)

def predict_labels(model, X):
    return model.predict(X)

def evaluate_model(model, X_test, Y_test):
    Y_pred = model.predict(X_test)
    print("\n[Evaluation Report]\n")
    print(classification_report(Y_test, Y_pred))
