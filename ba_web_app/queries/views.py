# -*- coding: utf-8 -*-
"""Query views."""
from flask import Blueprint, render_template, request
from ba_web_app.queries.forms import SubmitQueryForm
from ba_web_app.queries.models import Query

blueprint = Blueprint("queries", __name__, url_prefix="/queries", static_folder="../static")

@blueprint.route("/")
def index():
    """Query home page."""
    queries = Query.query.all()
    return render_template("queries/index.html", queries=queries)

@blueprint.route("/new/")
def create():
    """Submit a query."""
    form = SubmitQueryForm(request.form)
    return render_template("queries/submit.html", form=form)

@blueprint.route("/submit/", methods=["POST"])
def submit():
    """Submit a query."""
    form = SubmitQueryForm(request.form)

    #log the form data
    print(form.assistant.data)

    if form.validate_on_submit():
        # Save the query to the database
        query = Query.create(
            assistant=form.assistant.data,
            prompt=form.prompt.data,
            functions=form.functions.data,
        )
        return render_template("queries/submitted.html")

    return render_template("queries/submit.html", form=form)


