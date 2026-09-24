"""
data_manager.py
Single source of truth for reading/writing all CSV-backed data.
Every other module goes through here instead of touching CSV files directly.
"""

import os
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

IDEAS_CSV = os.path.join(DATA_DIR, "ideas.csv")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
NOTIF_CSV = os.path.join(DATA_DIR, "notifications.csv")
COMMENTS_CSV = os.path.join(DATA_DIR, "comments.csv")

IDEA_COLUMNS = [
    "id", "title", "description", "department", "category", "cost",
    "expected_impact", "submitted_by", "submitted_at", "status",
    "ai_category", "ai_summary", "ai_problem", "ai_improvements",
    "ai_requirements", "ai_implementation", "duplicate_of", "duplicate_score",
    "business_value", "feasibility", "cost_score", "strategic_alignment",
    "novelty", "potential_impact", "final_score",
    "reviewer", "reviewer_comment", "reviewed_at",
    "admin_comment", "approved_at", "implemented_at", "roi_estimate",
]

USER_COLUMNS = ["username", "password_hash", "role", "department", "full_name"]
NOTIF_COLUMNS = ["id", "username", "message", "link", "created_at", "is_read"]
COMMENT_COLUMNS = ["id", "idea_id", "username", "role", "comment", "created_at"]


def _ensure_csv(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)


def init_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    _ensure_csv(IDEAS_CSV, IDEA_COLUMNS)
    _ensure_csv(NOTIF_CSV, NOTIF_COLUMNS)
    _ensure_csv(COMMENTS_CSV, COMMENT_COLUMNS)

    if not os.path.exists(USERS_CSV):
        seed = pd.DataFrame([
            {"username": "admin", "password_hash": generate_password_hash("admin123"),
             "role": "admin", "department": "Management", "full_name": "Platform Admin"},
            {"username": "reviewer", "password_hash": generate_password_hash("reviewer123"),
             "role": "reviewer", "department": "Innovation Cell", "full_name": "Idea Reviewer"},
            {"username": "employee", "password_hash": generate_password_hash("employee123"),
             "role": "employee", "department": "Engineering", "full_name": "Demo Employee"},
        ], columns=USER_COLUMNS)
        seed.to_csv(USERS_CSV, index=False)


# ---------- generic helpers ----------

def _read(path, columns):
    if not os.path.exists(path):
        _ensure_csv(path, columns)
    # dtype=str + keep_default_na=False keeps every cell a plain string (no
    # NaN/float coercion), so mixed text+numeric columns never crash writes.
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df[columns]


def _write(path, df, columns):
    df = df.reindex(columns=columns)
    df.to_csv(path, index=False)


def _next_id(df):
    if df.empty:
        return 1
    ids = pd.to_numeric(df["id"], errors="coerce").fillna(0)
    return int(ids.max()) + 1


# ---------- users ----------

def get_users():
    return _read(USERS_CSV, USER_COLUMNS)


def get_user(username):
    df = get_users()
    row = df[df["username"].astype(str) == str(username)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def create_user(username, password, role, department, full_name):
    df = get_users()
    if not df[df["username"].astype(str) == str(username)].empty:
        return False, "Username already exists."
    new_row = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "department": department,
        "full_name": full_name,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _write(USERS_CSV, df, USER_COLUMNS)
    return True, "Account created."


# ---------- ideas ----------

def get_ideas_df():
    return _read(IDEAS_CSV, IDEA_COLUMNS)


def get_idea(idea_id):
    df = get_ideas_df()
    row = df[df["id"].astype(str) == str(idea_id)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def save_idea_row(idea_dict):
    """Insert a new idea row. Returns the assigned id."""
    df = get_ideas_df()
    new_id = _next_id(df)
    idea_dict = dict(idea_dict)
    idea_dict["id"] = new_id
    for c in IDEA_COLUMNS:
        idea_dict.setdefault(c, "")
    idea_dict = {k: ("" if v is None else str(v)) for k, v in idea_dict.items()}
    df = pd.concat([df, pd.DataFrame([idea_dict])], ignore_index=True)
    _write(IDEAS_CSV, df, IDEA_COLUMNS)
    return new_id


def update_idea(idea_id, updates: dict):
    df = get_ideas_df()
    mask = df["id"].astype(str) == str(idea_id)
    if not mask.any():
        return False
    for k, v in updates.items():
        if k in IDEA_COLUMNS:
            df.loc[mask, k] = "" if v is None else str(v)
    _write(IDEAS_CSV, df, IDEA_COLUMNS)
    return True


def ideas_by_user(username):
    df = get_ideas_df()
    return df[df["submitted_by"].astype(str) == str(username)].sort_values(
        "id", ascending=False
    )


def ideas_by_status(statuses):
    df = get_ideas_df()
    if isinstance(statuses, str):
        statuses = [statuses]
    return df[df["status"].isin(statuses)].sort_values("id", ascending=False)


def all_ideas_sorted():
    df = get_ideas_df()
    return df.sort_values("id", ascending=False)


# ---------- notifications ----------

def add_notification(username, message, link=""):
    df = _read(NOTIF_CSV, NOTIF_COLUMNS)
    new_id = _next_id(df)
    row = {
        "id": str(new_id), "username": username, "message": message, "link": link,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "is_read": "False",
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write(NOTIF_CSV, df, NOTIF_COLUMNS)


def get_notifications(username, unread_only=False):
    df = _read(NOTIF_CSV, NOTIF_COLUMNS)
    df = df[df["username"].astype(str) == str(username)]
    if unread_only:
        df = df[df["is_read"].astype(str).isin(["False", "0", "", "nan"])]
    return df.sort_values("id", ascending=False)


def mark_notifications_read(username):
    df = _read(NOTIF_CSV, NOTIF_COLUMNS)
    mask = df["username"].astype(str) == str(username)
    df.loc[mask, "is_read"] = "True"
    _write(NOTIF_CSV, df, NOTIF_COLUMNS)


def unread_count(username):
    return len(get_notifications(username, unread_only=True))


# ---------- comments ----------

def add_comment(idea_id, username, role, comment):
    df = _read(COMMENTS_CSV, COMMENT_COLUMNS)
    new_id = _next_id(df)
    row = {
        "id": str(new_id), "idea_id": str(idea_id), "username": username, "role": role,
        "comment": comment, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write(COMMENTS_CSV, df, COMMENT_COLUMNS)


def get_comments(idea_id):
    df = _read(COMMENTS_CSV, COMMENT_COLUMNS)
    return df[df["idea_id"].astype(str) == str(idea_id)].sort_values("id")
