# -*- coding: utf-8 -*-
"""AiExperiment views."""
import os
import datetime
import zipfile
from io import BytesIO

from flask import Blueprint, current_app, render_template, request, send_file
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

@blueprint.route("/view/<int:ai_experiment_id>/")
def view(ai_experiment_id):
    """View a AI Experiment."""
    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    responses = get_ai_responses(ai_experiment)

    return render_template("ai_experiments/view.html", ai_experiment=ai_experiment, ai_responses=responses)

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

@blueprint.route("/downloads/<int:ai_experiment_id>/")
def downloads(ai_experiment_id):
    """View a AI Experiment."""
    storage_directory = current_app.config["UPLOAD_FOLDER"]
    experiment_artifacts_directory = os.path.join(storage_directory, str(ai_experiment_id))
    directory_contents = os.listdir(experiment_artifacts_directory)
    #send the files to the user as a zip file
    #unless there is only one file, in which case just send that file
    if len(directory_contents) == 1:
        return send_from_directory(experiment_artifacts_directory, directory_contents[0])
    else:
        return send_from_directory(experiment_artifacts_directory, f"experiment_artifacts_{ai_experiment_id}.zip", True)

def send_from_directory(experiment_artifacts_directory, filename, compress=False):
    """Send a file from a directory to the user."""
    if compress:
        # Create a zip archive of the directory contents
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(experiment_artifacts_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, experiment_artifacts_directory)
                    zf.write(file_path, arcname)
        memory_file.seek(0)

        return send_file(memory_file, download_name=filename, as_attachment=True)

    else:
        return send_file(os.path.join(experiment_artifacts_directory, filename), as_attachment=True)

def get_ai_responses(ai_experiment):
    """Get the AI responses for an experiment."""
    responses = {}
    for file in ai_experiment.file_uploads:
        response = get_ai_response(ai_experiment.id, file)
        if response:
            responses[file.filename] = response

    return responses

def get_ai_response(ai_experiment_id, file):
    """Get the AI response for a file."""
    storage_directory = current_app.config["UPLOAD_FOLDER"]
    experiment_artifacts_directory = os.path.join(storage_directory, str(ai_experiment_id))

    file_base_name = file.filepath.split("/")[-1]
    file_base_name_without_extension, _ = os.path.splitext(file_base_name)

    response_file_path = os.path.join(experiment_artifacts_directory, file_base_name_without_extension + "_prompt.txt")

    if not os.path.exists(response_file_path):
        return None
    with open(response_file_path, "r") as f:
        return f.read()

