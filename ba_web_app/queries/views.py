# -*- coding: utf-8 -*-
"""Query views."""
import os

from flask import Blueprint, current_app, render_template, request
from werkzeug.utils import secure_filename

from ba_web_app.queries.forms import SubmitQueryForm
from ba_web_app.queries.models import FileUpload, Query

blueprint = Blueprint(
    "queries", __name__, url_prefix="/queries", static_folder="../static"
)


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
    """Handle submitted a query."""
    form = SubmitQueryForm(request.form)

    # check if the post request has the file part
    # if 'pdfFiles' not in request.files:
    #     flash('No file part')
    #     return redirect(request.url)

    flask_app = current_app._get_current_object()

    # log the form data
    print(form.assistant.data)

    if form.validate_on_submit():
        # Save the query to the database
        query = Query.create(
            assistant=form.assistant.data,
            prompt=form.prompt.data,
            functions=form.functions.data,
        )

        files = request.files.getlist("pdfFiles")
        file_uploads = []
        for file in files:
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(flask_app.config["UPLOAD_FOLDER"], filename))
                print("file.filename")
                print(file.filename)
                file_uploads.append(
                    FileUpload.create(
                        filename=file.filename,
                        filepath=os.path.join(
                            flask_app.config["UPLOAD_FOLDER"], filename
                        ),
                        file_type="pdf",
                        query_id=query.id,
                    )
                )

        return render_template("queries/submitted.html")

    return render_template("queries/submit.html", form=form)
