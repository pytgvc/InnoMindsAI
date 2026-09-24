"""
auth.py
Session-based login and role-based access control decorators.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
import data_manager as dm


def verify_login(username, password):
    user = dm.get_user(username)
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None


def current_user():
    """Returns the logged-in account, with 'role' overridden by the session's
    active role. Normally active role == real account role. In Demo Mode,
    active role can be switched (see /demo/switch-role) without a fresh
    login, so dashboards/nav/permission checks all follow the active role."""
    if "username" not in session:
        return None
    user = dm.get_user(session["username"])
    if user and session.get("role"):
        user = dict(user)
        user["role"] = session["role"]
    return user


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You don't have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator
