# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from ba_web_app.celery_utils import celery
from ba_web_app.extensions import login_manager
from ba_web_app.public.forms import LoginForm
from ba_web_app.user.forms import RegisterForm
from ba_web_app.user.models import User
from ba_web_app.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("You are logged in.", "success")
            redirect_url = request.args.get("next") or url_for("user.members")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("public/home.html", form=form)


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("public.home"))


@blueprint.route("/register/", methods=["GET", "POST"])
def register():
    """Register new user."""
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template("public/about.html", form=form)


@blueprint.route("/add", methods=["POST"])
def add():
    """Add two numbers.

    Basically "Hello World" for celery.
    Try:
    curl -X POST http://localhost:5000/add -H "Content-Type: application/json" -d '{"a": 10, "b": 20}'
    """
    from ba_web_app.tasks import add_numbers

    data = request.get_json()
    if not data or "a" not in data or "b" not in data:
        return jsonify({"error": "Please provide both a and b"}), 400

    task = add_numbers.delay(data["a"], data["b"])
    return jsonify({"message": "Task submitted successfully", "task_id": task.id}), 202


@blueprint.route("/status/<task_id>", methods=["GET"])
def status(task_id):
    """Get the status and result of a task."""
    task = celery.AsyncResult(task_id)
    response = {
        "status": task.state,
        "result": task.result if task.state == "SUCCESS" else None,
        "info": None,
    }
    if task.state == "FAILURE":
        response["info"] = str(task.info)  # Provide details if the task failed
    elif task.state == "PENDING":
        response["info"] = "Task is still pending"
    elif task.state == "STARTED" or task.state == "RETRY":
        response["info"] = "Task is in progress"
    return jsonify(response)
