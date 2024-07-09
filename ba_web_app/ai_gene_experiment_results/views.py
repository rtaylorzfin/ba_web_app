# -*- coding: utf-8 -*-
"""AiExperiment views."""
import json
import csv
import io

from flask import Blueprint, current_app, render_template, request, send_file, flash, redirect

from ba_web_app.ai_experiments.models import AiExperiment, AiGeneExperimentResult
from ba_web_app.ai_experiments.views import get_ai_responses, convert_ai_responses_to_csv

blueprint = Blueprint(
    "ai_gene_experiment_results", __name__, url_prefix="/ai_gene_experiment_results", static_folder="../static"
)


@blueprint.route("/view/<int:ai_experiment_id>/")
def view(ai_experiment_id):
    # config = read_config("/tmp/biocurator-assistant/config.cfg")
    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    ai_gene_experiment_result = ai_experiment.gene_experiment_result

    return render_template("ai_gene_experiment_results/view.html", ai_gene_experiment_result=ai_gene_experiment_result, ai_experiment=ai_experiment)


@blueprint.route("/create/<int:ai_experiment_id>/")
def create(ai_experiment_id):
    # config = read_config("/tmp/biocurator-assistant/config.cfg")
    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    uploads = ai_experiment.file_uploads
    first_upload = uploads[0]
    publication_name = first_upload.filename
    # ai_gene_experiment_result = AiGeneExperimentResult(ai_experiment_id=ai_experiment_id, publication_name=publication_name)

    return render_template("ai_gene_experiment_results/create.html", form=request.form, publication_name=publication_name, ai_experiment_id=ai_experiment_id)


@blueprint.route("/submit/", methods=["POST"])
def submit():
    # config = read_config("/tmp/biocurator-assistant/config.cfg")
    ai_experiment_id = request.form["ai_experiment_id"]
    publication_name = request.form["publication_name"]
    true_positives = request.form["true_positives"].strip()

    ai_experiment = AiExperiment.query.get(ai_experiment_id)
    responses = get_ai_responses(ai_experiment)
    responses_csv = convert_ai_responses_to_csv(responses, include_header=False)

    existing_result = ai_experiment.gene_experiment_result
    if existing_result:
        print("Deleting existing result")
        existing_result.delete()

    output = io.StringIO()
    csv_writer = csv.writer(output)
    for filename, content in responses_csv.items():
        for row in content.split("\n"):
            csv_writer.writerow([row])
    csv_string = output.getvalue()
    output.close()


    ai_gene_experiment_result = AiGeneExperimentResult(ai_experiment_id=ai_experiment_id,
                                                       publication_name=publication_name,
                                                       true_positives=true_positives,
                                                       # responses=json.dumps(responses),
                                                       responses_csv=csv_string)
    ai_gene_experiment_result.save()
    #ai_gene_experiment_result.save()
    print("ai_gene_experiment_result: ", publication_name)


    return render_template("ai_gene_experiment_results/submitted.html", form=request.form)


