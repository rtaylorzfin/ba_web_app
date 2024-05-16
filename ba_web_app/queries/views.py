# -*- coding: utf-8 -*-
"""Query views."""
from flask import Blueprint, render_template, request
from ba_web_app.queries.forms import SubmitQueryForm

blueprint = Blueprint("queries", __name__, url_prefix="/queries", static_folder="../static")


@blueprint.route("/")
def queries():
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
        render_template("queries/submitted.html")
    return render_template("queries/submit.html", form=form)
