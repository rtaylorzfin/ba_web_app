# -*- coding: utf-8 -*-
"""AiExperiment views."""
import os, datetime
from assistant import read_config

from flask import Blueprint, current_app, render_template, request
from werkzeug.utils import secure_filename

from ba_web_app.ai_experiments.forms import SubmitAiExperimentForm
from ba_web_app.ai_experiments.models import AiExperiment, AiFileUpload

blueprint = Blueprint(
    "ai_experiments", __name__, url_prefix="/ai_experiments", static_folder="../static"
)


@blueprint.route("/")
def index():
    """AI Experiment home page."""
    ai_experiments = AiExperiment.query.all()
    return render_template("ai_experiments/index.html", ai_experiments=ai_experiments)


@blueprint.route("/new/")
def create():
    """Submit a AI Experiment."""
    # config = read_config("/tmp/biocurator-assistant/config.cfg")
    form = SubmitAiExperimentForm(request.form)
    return render_template("ai_experiments/submit.html", form=form)


@blueprint.route("/submit/", methods=["POST"])
def submit():
    """Handle submitted a AI Experiment."""
    form = SubmitAiExperimentForm(request.form)

    # check if the post request has the file part
    # if 'pdfFiles' not in request.files:
    #     flash('No file part')
    #     return redirect(request.url)

    flask_app = current_app._get_current_object()

    # log the form data
    print(form.assistant.data)

    if form.validate_on_submit():
        # Save the AI Experiment to the database
        ai_experiment = AiExperiment.create(
            assistant=form.assistant.data,
            prompt=form.prompt.data,
            functions=form.functions.data,
        )

        files = request.files.getlist("pdfFiles")
        file_uploads = []
        for file in files:
            if file and file.filename != "":
                filename = secure_filename(file.filename)

                #does it already exist?
                persisted_filename = os.path.join(flask_app.config["UPLOAD_FOLDER"], filename)
                while os.path.exists(persisted_filename):
                    filename_with_timestamp = filename + "_" + str(datetime.datetime.now().timestamp())
                    persisted_filename = os.path.join(flask_app.config["UPLOAD_FOLDER"], filename_with_timestamp)

                file.save(persisted_filename)
                print("file.filename")
                print(file.filename)
                file_uploads.append(
                    AiFileUpload.create(
                        filename=file.filename,
                        filepath=persisted_filename,
                        file_type="pdf",
                        ai_experiment_id=ai_experiment.id,
                    )
                )

        return render_template("ai_experiments/submitted.html")

    return render_template("ai_experiments/submit.html", form=form)
