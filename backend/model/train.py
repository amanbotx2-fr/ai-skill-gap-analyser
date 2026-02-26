"""
train.py — AI Skill Gap Analyser
Hackathon ML Pipeline: Synthetic Data → Feature Engineering → Model Training → Export
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ─────────────────────────────────────────────
# STEP 1: Synthetic Dataset Generation
# ─────────────────────────────────────────────

def generate_dataset(n_samples: int = 450, random_state: int = 42) -> pd.DataFrame:
    """
    Generate synthetic student quiz performance data.
    Each row represents one student's performance across key CS topics.
    """
    rng = np.random.default_rng(random_state)

    # Simulate per-topic accuracy scores (0–100%)
    ds_accuracy       = rng.uniform(10, 100, n_samples)   # Data Structures
    algo_accuracy     = rng.uniform(10, 100, n_samples)   # Algorithms
    dbms_accuracy     = rng.uniform(10, 100, n_samples)   # Database Management
    os_accuracy       = rng.uniform(10, 100, n_samples)   # Operating Systems

    # avg_time: seconds taken per question (faster isn't always better — noise added)
    avg_time          = rng.uniform(15, 120, n_samples)

    # overall_score: weighted average of topic accuracies with slight noise
    overall_score = (
        0.30 * ds_accuracy +
        0.30 * algo_accuracy +
        0.20 * dbms_accuracy +
        0.20 * os_accuracy +
        rng.normal(0, 3, n_samples)        # small real-world noise
    ).clip(0, 100)

    # weakest_topic_score: the lowest accuracy across the four topics for each student
    topic_matrix      = np.stack([ds_accuracy, algo_accuracy, dbms_accuracy, os_accuracy], axis=1)
    weakest_topic_score = topic_matrix.min(axis=1)

    df = pd.DataFrame({
        "ds_accuracy":        ds_accuracy.round(2),
        "algo_accuracy":      algo_accuracy.round(2),
        "dbms_accuracy":      dbms_accuracy.round(2),
        "os_accuracy":        os_accuracy.round(2),
        "avg_time":           avg_time.round(2),
        "overall_score":      overall_score.round(2),
        "weakest_topic_score": weakest_topic_score.round(2),
    })

    return df


# ─────────────────────────────────────────────
# STEP 2: Mastery Label Assignment
# ─────────────────────────────────────────────

def assign_mastery_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign mastery_label based on overall_score:
      0 → Beginner    (overall_score < 50)
      1 → Developing  (50 ≤ overall_score < 75)
      2 → Proficient  (overall_score ≥ 75)
    """
    def label(score):
        if score < 50:
            return 0   # Beginner
        elif score < 75:
            return 1   # Developing
        else:
            return 2   # Proficient

    df["mastery_label"] = df["overall_score"].apply(label)
    return df


# ─────────────────────────────────────────────
# STEP 3: Train/Test Split & Model Training
# ─────────────────────────────────────────────

def train_model(df: pd.DataFrame):
    """
    Split data, train a RandomForestClassifier, and report accuracy.
    Returns the trained model, plus X_test / y_test for evaluation.
    """
    FEATURE_COLS = [
        "ds_accuracy",
        "algo_accuracy",
        "dbms_accuracy",
        "os_accuracy",
        "avg_time",
        "overall_score",
        "weakest_topic_score",
    ]
    TARGET_COL = "mastery_label"

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    # 80/20 stratified split — keeps class distribution balanced
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Random Forest: robust to feature scale, handles small datasets well
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=None,         # let trees grow fully — dataset is small
        random_state=42,
        class_weight="balanced" # handles any class imbalance gracefully
    )
    model.fit(X_train, y_train)

    # ── Evaluation ──────────────────────────────
    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc  = accuracy_score(y_test,  model.predict(X_test))

    print("\n" + "═" * 45)
    print("  AI SKILL GAP ANALYSER — Training Report")
    print("═" * 45)
    print(f"  Dataset shape    : {df.shape}")
    print(f"  Training samples : {len(X_train)}  |  Test samples: {len(X_test)}")
    print(f"  Training accuracy: {train_acc * 100:.2f}%")
    print(f"  Testing  accuracy: {test_acc  * 100:.2f}%")
    print("\n── Per-Class Report (Test Set) ──")
    label_names = ["Beginner", "Developing", "Proficient"]
    print(classification_report(y_test, model.predict(X_test), target_names=label_names))
    print("═" * 45 + "\n")

    return model


# ─────────────────────────────────────────────
# STEP 4: Save Outputs
# ─────────────────────────────────────────────

def save_outputs(df: pd.DataFrame, model, dataset_path: str = "dataset.csv", model_path: str = "model.pkl"):
    """
    Persist the dataset and trained model to disk.
    """
    df.to_csv(dataset_path, index=False)
    print(f"  ✔ Dataset saved  → {dataset_path}  ({len(df)} rows)")

    joblib.dump(model, model_path)
    print(f"  ✔ Model saved    → {model_path}")


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    print("\n[1/4] Generating synthetic dataset …")
    df = generate_dataset(n_samples=450)

    print("[2/4] Assigning mastery labels …")
    df = assign_mastery_label(df)

    print("[3/4] Training RandomForest model …")
    model = train_model(df)

    print("[4/4] Saving outputs …")
    save_outputs(df, model)

    print("\n  Pipeline complete. Ready for inference!\n")


if __name__ == "__main__":
    main()