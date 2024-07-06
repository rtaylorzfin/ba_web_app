# -*- coding: utf-8 -*-
"""AiExperiment views."""
import os
import datetime
import zipfile
import json
from io import BytesIO

from flask import Blueprint, current_app, render_template, request, send_file, flash, redirect
from werkzeug.utils import secure_filename
from sqlalchemy import desc

from ba_web_app.ai_experiments.forms import SubmitAiExperimentForm
from ba_web_app.ai_experiments.models import AiExperiment, AiFileUpload
from ba_web_app.ai_utils.client import submit_experiment

blueprint = Blueprint(
    "ai_experiments", __name__, url_prefix="/ai_experiments", static_folder="../static"
)

@blueprint.route("/")
def index():
    """AI Experiment home page."""
    ai_experiments = AiExperiment.query.order_by(desc(AiExperiment.created_at)).order_by(desc(AiExperiment.id)).all()
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
    csv_responses = convert_ai_responses_to_csv(responses)

    return render_template("ai_experiments/view.html", ai_experiment=ai_experiment, ai_responses=responses, csv_responses=csv_responses)

@blueprint.route("/submit/", methods=["POST"])
def submit():
    """Handle submitted a AI Experiment."""
    form = SubmitAiExperimentForm(request.form)

    # check if the post request has the file part
    if 'pdfFiles' not in request.files:
        flash('No file part')
        return redirect(request.url)

    flask_app = current_app._get_current_object()

    # log the form data
    print(form.assistant.data)

    if form.validate_on_submit():
        # Save the AI Experiment to the database
        ai_experiment = AiExperiment.create(
            name=form.name.data,
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

        return render_template("ai_experiments/submitted.html", ai_experiment=ai_experiment)

    return render_template("ai_experiments/submit.html", form=form)

@blueprint.route("/downloads/<int:ai_experiment_id>/")
def downloads(ai_experiment_id):
    """Create a zip file with text files inside."""
    files = []
    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    responses = get_ai_responses(ai_experiment)
    csv_responses = convert_ai_responses_to_csv(responses)

    for filename, content in responses.items():
        filename = filename.replace(".pdf", ".txt")
        files.append({"filename": filename, "content": content})

    for filename, content in csv_responses.items():
        filename = filename.replace(".pdf", "")
        files.append({"filename": filename + ".csv", "content": content})

    files.append({"filename": "assistant-definition.txt", "content": ai_experiment.assistant})
    files.append({"filename": "prompt.txt", "content": ai_experiment.prompt})
    files.append({"filename": "functions.json", "content": ai_experiment.functions})

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.writestr(file["filename"], file["content"])

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"ai_experiment_{ai_experiment_id}.zip", as_attachment=True)

@blueprint.route("/clone/<int:ai_experiment_id>/")
def clone(ai_experiment_id):
    """Clone a AI Experiment."""
    ai_experiment = AiExperiment.query.get(ai_experiment_id)

    prefill_data = {
        # 'name': ai_experiment.name,
        'assistant': ai_experiment.assistant,
        'prompt': ai_experiment.prompt,
        'functions': ai_experiment.functions,
    }

    form = SubmitAiExperimentForm(data=prefill_data)
    return render_template("ai_experiments/submit.html", form=form)


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


def convert_ai_response_to_csv(response_json):
    """Convert AI response to CSV.
    Expecting a parent term with array of children to convert to CSV.
    """
    try:
        response = json.loads(response_json)
        parent_terms = response.items()
    except Exception as e:
        print(f"Error converting AI response to CSV: {e}")
        return ""
    if len(parent_terms) == 0:
        print("CSV error: No parent terms found in response")
        return ""
    if len(parent_terms) > 1:
        print("CSV error: Multiple parent terms found in response")
        return ""

    csv_rows = []
    headers = []
    for parent_key, children in response.items():
        for child in children:
            for key, value in child.items():
                if key not in headers:
                    headers.append(key)
            csv_row = []
            for header in headers:
                if header in child:
                    csv_row.append(child[header])
                else:
                    csv_row.append("")
            csv_rows.append(csv_row)

    csv_rows.insert(0, headers)
    return "\n".join(["\t".join(row) for row in csv_rows])



def convert_ai_responses_to_csv(responses):
    """Convert AI responses to CSV."""
    csv_responses = {}
    for filename, response in responses.items():
        csv_responses[filename] = convert_ai_response_to_csv(response)

    return csv_responses

