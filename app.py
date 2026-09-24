"""
app.py
InnoMinds AI - AI-Powered Innovation Management Platform (SIH 2026, IS-1)
Flask application entry point.
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

import data_manager as dm
import ai_analysis
import duplicate_detector
import evaluation
from auth import verify_login, current_user, login_required, role_required

app = Flask(__name__)
app.secret_key = os.environ.get("INNOMINDS_SECRET", "dev-secret-change-me")

DEPARTMENTS = [
    "Engineering", "Operations", "HR", "Finance", "Marketing",
    "Customer Support", "IT", "Quality & Safety", "Management",
]
CATEGORIES = [
    "Process Improvement", "Cost Reduction", "Technology & Automation",
    "Customer Experience", "Sustainability", "Product Innovation",
    "Workplace & HR", "Safety & Risk",
]
STATUS_FLOW = ["Submitted", "Under Review", "Pending Approval", "Approved", "Implemented", "Rejected"]

dm.init_storage()


@app.context_processor
def inject_globals():
    user = current_user()
    unread = dm.unread_count(user["username"]) if user else 0
    return dict(current_user=user, unread_count=unread, now_year=datetime.now().year,
                real_role=session.get("real_role"))


# ---------------- auth ----------------

@app.route("/", methods=["GET"])
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip().lower()
        user = verify_login(username, password)
        if user and selected_role and user["role"] != selected_role:
            flash(f"That account is registered as '{user['role'].capitalize()}', "
                  f"not '{selected_role.capitalize()}'. Please select the correct role.", "danger")
        elif user:
            session["username"] = user["username"]
            session["real_role"] = user["role"]
            session["role"] = user["role"]  # active/viewing role - switchable in-session via the role hub
            session["full_name"] = user["full_name"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("role_hub"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/role-hub")
@login_required
def role_hub():
    """Landing screen shown right after login and reachable anytime via
    'Switch Role' in the sidebar. Lets the same logged-in session move
    between Employee / Reviewer / Admin views with no logout required."""
    return render_template("role_hub.html")


@app.route("/switch-role/<role>")
@login_required
def switch_role(role):
    """Switches the active/viewing role for this session without logging
    out. Does not touch the real account role stored in users.csv."""
    role = role.strip().lower()
    if role not in ("employee", "reviewer", "admin"):
        flash("Unknown role.", "danger")
        return redirect(url_for("dashboard"))
    session["role"] = role
    flash(f"Now viewing as {role.capitalize()}.", "info")
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", DEPARTMENTS[0])
        if not username or not password or not full_name:
            flash("All fields are required.", "danger")
        else:
            ok, msg = dm.create_user(username, password, "employee", department, full_name)
            flash(msg, "success" if ok else "danger")
            if ok:
                return redirect(url_for("login"))
    return render_template("register.html", departments=DEPARTMENTS)


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ---------------- dashboard ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    df = dm.get_ideas_df()

    if user["role"] == "employee":
        mine = dm.ideas_by_user(user["username"])
        stats = {
            "total": len(mine),
            "pending": len(mine[mine["status"].isin(["Submitted", "Under Review", "Pending Approval"])]),
            "approved": len(mine[mine["status"].isin(["Approved", "Implemented"])]),
            "rejected": len(mine[mine["status"] == "Rejected"]),
        }
        return render_template("dashboard.html", role="employee", stats=stats,
                                ideas=mine.head(6).to_dict("records"))

    if user["role"] == "reviewer":
        queue = dm.ideas_by_status(["Submitted", "Under Review"])
        stats = {
            "total": len(df),
            "queue": len(queue),
            "forwarded": len(df[df["status"] == "Pending Approval"]),
            "reviewed_by_me": len(df[df["reviewer"] == user["username"]]),
        }
        return render_template("dashboard.html", role="reviewer", stats=stats,
                                ideas=queue.head(6).to_dict("records"))

    # admin
    stats = {
        "total": len(df),
        "pending_approval": len(df[df["status"] == "Pending Approval"]),
        "approved": len(df[df["status"].isin(["Approved", "Implemented"])]),
        "implemented": len(df[df["status"] == "Implemented"]),
        "rejected": len(df[df["status"] == "Rejected"]),
    }
    top = evaluation.top_priority_ideas(df, n=5)
    return render_template("dashboard.html", role="admin", stats=stats,
                            ideas=df.sort_values("id", ascending=False).head(6).to_dict("records"),
                            top_ideas=top.to_dict("records"))


# ---------------- idea submission ----------------

@app.route("/submit", methods=["GET", "POST"])
@role_required("employee")
def submit_idea():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        department = request.form.get("department", "")
        category = request.form.get("category", "")
        cost = request.form.get("cost", "0")
        expected_impact = request.form.get("expected_impact", "").strip()

        errors = []
        if not title or len(title) < 5:
            errors.append("Title must be at least 5 characters.")
        if not description or len(description) < 20:
            errors.append("Description must be at least 20 characters so AI analysis is meaningful.")
        try:
            cost_val = float(cost)
            if cost_val < 0:
                errors.append("Cost cannot be negative.")
        except ValueError:
            errors.append("Cost must be a number.")
            cost_val = 0

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("submit_idea.html", departments=DEPARTMENTS, categories=CATEGORIES,
                                    form=request.form)

        user = current_user()
        ai_result = ai_analysis.analyze_idea(title, description, department, category, cost_val)

        existing = dm.get_ideas_df().to_dict("records")
        dup_id, dup_score, related = duplicate_detector.find_duplicates(title, description, existing)

        idea = {
            "title": title, "description": description, "department": department,
            "category": category or ai_result["ai_category"], "cost": cost_val,
            "expected_impact": expected_impact, "submitted_by": user["username"],
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "Submitted", "duplicate_of": dup_id or "", "duplicate_score": dup_score,
            **ai_result,
        }
        new_id = dm.save_idea_row(idea)

        if dup_id:
            flash(f"Idea submitted, but it looks similar to idea #{dup_id} "
                  f"(similarity {dup_score:.0%}). A reviewer will check this.", "warning")
        else:
            flash("Idea submitted successfully! AI analysis has been generated.", "success")

        return redirect(url_for("idea_detail", idea_id=new_id))

    return render_template("submit_idea.html", departments=DEPARTMENTS, categories=CATEGORIES, form={})


@app.route("/my-ideas")
@role_required("employee")
def my_ideas():
    user = current_user()
    mine = dm.ideas_by_user(user["username"])
    return render_template("my_ideas.html", ideas=mine.to_dict("records"))


# ---------------- idea detail / lifecycle actions ----------------

@app.route("/idea/<int:idea_id>")
@login_required
def idea_detail(idea_id):
    idea = dm.get_idea(idea_id)
    if not idea:
        flash("Idea not found.", "danger")
        return redirect(url_for("dashboard"))

    user = current_user()
    if user["role"] == "employee" and idea["submitted_by"] != user["username"]:
        flash("You can only view your own ideas.", "danger")
        return redirect(url_for("dashboard"))

    comments = dm.get_comments(idea_id).to_dict("records")
    chart_path = f"charts/idea_{idea_id}.png"
    chart_exists = os.path.exists(os.path.join("static", chart_path))
    return render_template("idea_detail.html", idea=idea, comments=comments,
                            chart_path=chart_path if chart_exists else None)


@app.route("/review-queue")
@role_required("reviewer", "admin")
def review_queue():
    queue = dm.ideas_by_status(["Submitted", "Under Review"])
    return render_template("queue.html", title="Review Queue", ideas=queue.to_dict("records"),
                            empty_msg="No ideas waiting for review.")


@app.route("/approval-queue")
@role_required("admin")
def approval_queue():
    queue = dm.ideas_by_status(["Pending Approval"])
    return render_template("queue.html", title="Approval Queue", ideas=queue.to_dict("records"),
                            empty_msg="No ideas waiting for final approval.")


@app.route("/evaluate/<int:idea_id>", methods=["POST"])
@role_required("reviewer", "admin")
def evaluate(idea_id):
    idea = dm.get_idea(idea_id)
    if not idea:
        flash("Idea not found.", "danger")
        return redirect(url_for("review_queue"))

    user = current_user()
    try:
        scores = {
            "business_value": float(request.form.get("business_value", 5)),
            "feasibility": float(request.form.get("feasibility", 5)),
            "strategic_alignment": float(request.form.get("strategic_alignment", 5)),
            "novelty": float(request.form.get("novelty", 5)),
            "potential_impact": float(request.form.get("potential_impact", 5)),
        }
        for k, v in scores.items():
            if not (0 <= v <= 10):
                raise ValueError(f"{k} must be between 0 and 10.")
    except ValueError as e:
        flash(f"Invalid score input: {e}", "danger")
        return redirect(url_for("idea_detail", idea_id=idea_id))

    result = evaluation.score_idea(idea_id, cost=idea["cost"], **scores)
    comment = request.form.get("comment", "").strip()
    decision = request.form.get("decision", "forward")  # forward | reject

    updates = {
        **result,
        "reviewer": user["username"],
        "reviewer_comment": comment,
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Pending Approval" if decision == "forward" else "Rejected",
    }
    dm.update_idea(idea_id, updates)
    if comment:
        dm.add_comment(idea_id, user["username"], user["role"], comment)

    dm.add_notification(
        idea["submitted_by"],
        f"Your idea '{idea['title']}' was {'forwarded to admin for approval' if decision=='forward' else 'rejected'} by reviewer {user['username']}.",
        link=url_for("idea_detail", idea_id=idea_id),
    )
    flash("Evaluation saved.", "success")
    return redirect(url_for("idea_detail", idea_id=idea_id))


@app.route("/decide/<int:idea_id>", methods=["POST"])
@role_required("admin")
def decide(idea_id):
    idea = dm.get_idea(idea_id)
    if not idea:
        flash("Idea not found.", "danger")
        return redirect(url_for("approval_queue"))

    user = current_user()
    action = request.form.get("action")  # approve | reject | implement
    admin_comment = request.form.get("admin_comment", "").strip()
    roi_estimate = request.form.get("roi_estimate", "")

    updates = {"admin_comment": admin_comment}
    if action == "approve":
        updates.update({
            "status": "Approved",
            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "roi_estimate": roi_estimate or idea.get("roi_estimate", ""),
        })
        msg = f"Your idea '{idea['title']}' has been APPROVED!"
    elif action == "reject":
        updates.update({"status": "Rejected"})
        msg = f"Your idea '{idea['title']}' was rejected at final approval."
    elif action == "implement":
        updates.update({"status": "Implemented", "implemented_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
        msg = f"Great news -- your idea '{idea['title']}' has been marked as IMPLEMENTED."
    else:
        flash("Unknown action.", "danger")
        return redirect(url_for("idea_detail", idea_id=idea_id))

    dm.update_idea(idea_id, updates)
    if admin_comment:
        dm.add_comment(idea_id, user["username"], user["role"], admin_comment)
    dm.add_notification(idea["submitted_by"], msg, link=url_for("idea_detail", idea_id=idea_id))
    flash("Decision recorded.", "success")
    return redirect(url_for("idea_detail", idea_id=idea_id))


# ---------------- analytics ----------------

@app.route("/analytics")
@role_required("reviewer", "admin")
def analytics():
    df = dm.get_ideas_df()
    charts = {
        "status": evaluation.status_distribution_chart(df),
        "department": evaluation.department_contribution_chart(df),
        "progress": evaluation.implementation_progress_chart(df),
        "roi": evaluation.roi_chart(df),
    }
    recommendations = evaluation.department_resource_recommendation(df)
    trend = evaluation.trend_recommendation(df)
    top = evaluation.top_priority_ideas(df, n=5)
    return render_template("analytics.html", charts=charts, recommendations=recommendations,
                            trend=trend, top_ideas=top.to_dict("records"))


# ---------------- notifications ----------------

@app.route("/notifications")
@login_required
def notifications():
    user = current_user()
    notes = dm.get_notifications(user["username"])
    dm.mark_notifications_read(user["username"])
    return render_template("notifications.html", notes=notes.to_dict("records"))


@app.route("/api/notifications/count")
@login_required
def api_unread_count():
    user = current_user()
    return jsonify({"count": dm.unread_count(user["username"])})


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
