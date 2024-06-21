# -*- coding: utf-8 -*-
"""AiExperiment views."""
import os, datetime

from flask import Blueprint, current_app, render_template, request
from werkzeug.utils import secure_filename

from ba_web_app.ai_experiments.forms import SubmitAiExperimentForm
from ba_web_app.ai_experiments.models import AiExperiment, AiFileUpload
from ba_web_app.ai_utils.client import submit_experiment

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

        # The files that were uploaded with the form as "pdfFiles"
        uploaded_pdf_files = request.files.getlist("pdfFiles")

        # Save the uploaded files to the database as AiFileUpload objects
        ai_file_uploads = []
        for file in uploaded_pdf_files:
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file_without_extension, file_extension = os.path.splitext(filename)

                #does it already exist?
                persisted_filename = os.path.join(flask_app.config["UPLOAD_FOLDER"], filename)
                while os.path.exists(persisted_filename):
                    timestamp = str(datetime.datetime.now().timestamp()).replace(".", "")
                    filename_with_timestamp = file_without_extension + "_" + timestamp + file_extension
                    persisted_filename = os.path.join(flask_app.config["UPLOAD_FOLDER"], filename_with_timestamp)

                file.save(persisted_filename)
                print("file.filename")
                print(file.filename)
                print("persisted_filename")
                print(persisted_filename)
                ai_file_uploads.append(
                    AiFileUpload.create(
                        filename=file.filename,
                        filepath=persisted_filename,
                        file_type="pdf",
                        ai_experiment_id=ai_experiment.id,
                    )
                )

        filepaths = [f.filepath for f in ai_file_uploads]
        submit_experiment(api_key=flask_app.config["OPENAI_API_KEY"],
                         assistant_instructions=ai_experiment.assistant,
                         prompt=ai_experiment.prompt,
                         functions=ai_experiment.functions,
                         files=filepaths,
                          unique_id=str(ai_experiment.id))

        return render_template("ai_experiments/submitted.html")

    return render_template("ai_experiments/submit.html", form=form)
