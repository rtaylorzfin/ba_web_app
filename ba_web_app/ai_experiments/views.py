# -*- coding: utf-8 -*-
"""AiExperiment views."""
import datetime
import hashlib
import json
import os
import uuid
import zipfile
from io import BytesIO

import pandas as pd
from flask import Blueprint, current_app, render_template, request, send_file, flash, redirect
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from ba_web_app.ai_experiments.forms import SubmitAiExperimentForm
from ba_web_app.ai_experiments.models import AiExperiment, AiFileUpload, AiGeneAlias
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

    # The experiment group ID is used to group multiple experiments together
    # Use a UUID or similar to group experiments together
    experiment_group_id = uuid.uuid4().hex

    if not form.validate_on_submit():
        flash("Invalid form data")
        return render_template("ai_experiments/submit.html", form=form)

    # The files that were uploaded with the form as "pdfFiles"
    uploaded_pdf_files = request.files.getlist("pdfFiles")

    ai_experiment = None
    if form.save_files_separately:
        print("Saving each file as a separate experiment")
        for file in uploaded_pdf_files:
            ai_experiment = process_experiment(experiment_group_id, flask_app, form, [file])
    else:
        print("Saving all files as a single experiment")
        ai_experiment = process_experiment(experiment_group_id, flask_app, form, uploaded_pdf_files)

    return render_template("ai_experiments/submitted.html", ai_experiment=ai_experiment)


def process_experiment(experiment_group_id, flask_app, form, uploaded_pdf_files):
    # Save the AI Experiment to the database
    ai_experiment = AiExperiment.create(
        group_id=experiment_group_id,
        name=form.name.data,
        assistant=form.assistant.data,
        prompt=form.prompt.data,
        functions=form.functions.data,
    )
    # Save the uploaded files to the database as AiFileUpload objects
    ai_file_uploads = []
    for file in uploaded_pdf_files:
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file_without_extension, file_extension = os.path.splitext(filename)

            # does it already exist?
            persisted_filename = os.path.join(flask_app.config["UPLOAD_FOLDER"], filename)
            uploaded_file_hash = hash_file(file)

            while os.path.exists(persisted_filename):
                # Is the existing file the same as the uploaded file?
                with open(persisted_filename, 'rb') as f:
                    persisted_file_hash = hashlib.sha256(f.read()).hexdigest()
                if uploaded_file_hash == persisted_file_hash:
                    print(f"File already exists with same name and contents: {filename}")
                    break
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
    return ai_experiment

@blueprint.route("/group_download/<string:ai_experiment_group_id>/")
def group_download(ai_experiment_group_id):
    """Download a group of AI Experiments."""
    ai_experiments = AiExperiment.query.filter_by(group_id=ai_experiment_group_id).all()

    #create a zip file with a subdirectory for each experiment
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for ai_experiment in ai_experiments:
            files = get_file_contents_for_experiment(ai_experiment)

            # Create a subdirectory for the experiment
            experiment_dir = f"experiment_{ai_experiment.id}/"

            for file in files:
                filepath = experiment_dir + file["filename"]
                zf.writestr(filepath, file["content"])

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"ai_experiment_group_{ai_experiment_group_id}.zip", as_attachment=True)



@blueprint.route("/group_summary/<string:ai_experiment_group_id>/")
def group_summary(ai_experiment_group_id):
    """Download a summary of AI Experiments."""
    ai_experiments = AiExperiment.query.filter_by(group_id=ai_experiment_group_id).all()

    # Create a DataFrame to store the data
    data = []

    # Write the headers
    headers = ["Experiment ID", "Filename", "Gene", "Status", "Result", "Details", "Current Gene"]

    for ai_experiment in ai_experiments:
        responses = get_ai_responses(ai_experiment)
        csv_responses = convert_ai_responses_to_csv(responses, include_header=False)
        print("Getting gene experiment result for experiment", ai_experiment.id)
        ai_gene_experiment_result = ai_experiment.gene_experiment_result

        for filename, content in csv_responses.items():
            found_genes = content.split("\n")
            distinct_genes = set(found_genes)
            for row in distinct_genes:
                row = row.strip().lower()
                indexed = ""
                result_column = ""
                current_gene = ""
                true_positives = ai_gene_experiment_result.true_positives.split("\n") if ai_gene_experiment_result else []
                true_positives = list(map(str.strip, true_positives))
                true_positives = [x.lower() for x in true_positives]
                if row in true_positives:
                    indexed = "Indexed"
                    result_column = "True positive"
                    current_gene = row
                else:
                    #check for alias
                    alias_match = AiGeneAlias.query.filter_by(alias=row).first()
                    if alias_match:
                        alias_gene = alias_match.gene
                        current_gene = alias_gene
                        if alias_gene.lower() in true_positives:
                            indexed = "Indexed"
                            result_column = "true positive -symbol mismatch"

                data.append([ai_experiment.id, filename, row, indexed, result_column, "", current_gene])

    # Create a DataFrame from the data
    df = pd.DataFrame(data, columns=headers)

    # sort the DataFrame by Experiment ID, then by Gene
    df = df.sort_values(by=["Experiment ID", "Gene"])

    # Save the DataFrame to a BytesIO object as an Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write the summary sheet
        df.to_excel(writer, index=False, sheet_name='Summary')

        # Get the workbook and worksheet objects
        workbook  = writer.book
        summary_sheet = writer.sheets['Summary']

        # Adjust the column widths in the summary sheet
        for i, column in enumerate(df.columns):
            column_length = max(df[column].astype(str).map(len).max(), len(column)) + 2
            summary_sheet.set_column(i, i, column_length)

        # Write the second sheet
        details_sheet = workbook.add_worksheet('config')
        first_experiment = ai_experiments[0]
        details = [
            ("Experiment Name", first_experiment.name),
            ("Assistant", first_experiment.assistant),
            ("Prompt", first_experiment.prompt),
            ("Functions", first_experiment.functions)
        ]

        for row_idx, (header, value) in enumerate(details):
            details_sheet.write(row_idx, 0, header)
            details_sheet.write(row_idx, 1, value)

        # Adjust the column widths in the config sheet
        for col_idx, _ in enumerate(details[0]):
            column_length = max([len(str(details[row_idx][col_idx])) for row_idx in range(len(details))]) + 2
            details_sheet.set_column(col_idx, col_idx, column_length)

    output.seek(0)

    return send_file(output, download_name=f"ai_experiment_group_{ai_experiment_group_id}.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@blueprint.route("/downloads/<int:ai_experiment_id>/")
def downloads(ai_experiment_id):
    """Create a zip file with text files inside."""

    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    files = get_file_contents_for_experiment(ai_experiment)

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.writestr(file["filename"], file["content"])

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"ai_experiment_{ai_experiment_id}.zip", as_attachment=True)


def get_file_contents_for_experiment(ai_experiment):
    files = []
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
    return files


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

@blueprint.route("/delete/<int:ai_experiment_id>/")
def delete(ai_experiment_id):
    """Delete a AI Experiment."""

    #Check if it is a POST request
    if request.method == 'POST':
        ai_experiment = AiExperiment.query.get(ai_experiment_id)
        ai_experiment.delete()
        return redirect("/ai_experiments/")

    # return render_template("ai_experiments/delete.html", ai_experiment_id=ai_experiment_id)

@blueprint.route("/group/<string:ai_experiment_group_id>")
def group(ai_experiment_group_id):
    """View a group of AI Experiments."""
    ai_experiments = AiExperiment.query.filter_by(group_id=ai_experiment_group_id).all()
    return render_template("ai_experiments/group.html", ai_experiment_group_id=ai_experiment_group_id,  ai_experiments=ai_experiments)

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

def convert_ai_response_to_csv(response_json, include_header=True):
    """Convert AI response to CSV.
    Expecting a parent term with array of children to convert to CSV.
    """
    try:
        response = json.loads(response_json)
        parent_terms = response.items()
    except Exception as e:
        print(f"Error converting AI response to CSV: {e}")
        print("Trying to use raw response as list")
        return response_json
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

    if include_header:
        csv_rows.insert(0, headers)
    return "\n".join(["\t".join(row) for row in csv_rows])

def convert_ai_responses_to_csv(responses, include_header=True):
    """Convert AI responses to CSV."""
    csv_responses = {}
    for filename, response in responses.items():
        csv_responses[filename] = convert_ai_response_to_csv(response, include_header)

    return csv_responses

def hash_file(file):
    hasher = hashlib.sha256()
    # Read file content in chunks to avoid memory issues with large files
    for chunk in iter(lambda: file.read(4096), b""):
        hasher.update(chunk)
    file.seek(0)  # Reset file pointer after reading
    return hasher.hexdigest()