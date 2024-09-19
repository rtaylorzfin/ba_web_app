import hashlib
import os
import json
import time
from tempfile import mkstemp
from pathlib import Path

import yaml
from openai import OpenAI
from assistant import get_or_create_biocurator_assistant, process_input_files, cleanup_resources, create_vector_store
from flask import current_app

def submit_experiment(api_key, assistant_instructions, prompt, functions, files, unique_id):
    assistant_id = None

    # Create a temp file for functions as json file:
    functions_json_path = create_temp_json()
    with open(functions_json_path, 'w') as f:
        f.write(functions)

    prompt_as_dict = {'prompt': prompt}
    prompts_yaml_path = create_temp_yaml_from_dictionary(prompt_as_dict)

    try:
        # Initializing the OpenAI client with the API key from the command line
        client = OpenAI(api_key=api_key)

        # Configuration for the assistant
        flask_app = current_app._get_current_object()
        config = {
            'DEFAULT': {
                'model': flask_app.config["GPT_MODEL"],
                'assistant_instructions': assistant_instructions,
                'prompts_yaml_file': prompts_yaml_path,
                'output_dir': flask_app.config["UPLOAD_FOLDER"] + "/" + unique_id,
                'timeout_seconds': 600
            }
        }

        # Make sure the output directory exists
        if Path(config['DEFAULT']['output_dir']).exists() is False:
            print(f"Output directory does not exist, creating : {config['DEFAULT']['output_dir']}")
            Path(config['DEFAULT']['output_dir']).mkdir(parents=True)

        if Path(config['DEFAULT']['output_dir']).exists() is False:
            raise Exception(f"Could not create output directory: {config['DEFAULT']['output_dir']}")

        vector_store_id = create_vector_store(client)
        assistant_id = get_or_create_biocurator_assistant(client, config, functions_json_path, vector_store_id)

        # Get the list of files to process
        # input_files = [file.filename for file in files]

        # Start the processing timer
        start_time = time.time()

        # Process each file
        files_as_paths = [Path(file) for file in files]
        process_input_files(client, assistant_id, vector_store_id, files_as_paths, config)

        # Calculate and print the total time elapsed
        end_time = time.time()
        total_time_elapsed = end_time - start_time
        print(f"Total time elapsed: {total_time_elapsed:.2f} seconds")

        # Calculate the average time per file
        if len(files) > 0:
            average_time_per_file = total_time_elapsed / len(files)
            print(f"Average time per input file: {average_time_per_file:.2f} seconds")
        else:
            print("No files were processed.")

    except Exception as e:
        print(f"An error occurred: {e}", flush=True)

    finally:
        cleanup_resources(client, vector_store_id, assistant_id)


def create_temp_json():
    """Create a temporary file for the functions as a JSON file."""
    return mkstemp(suffix='.json')[1]

def create_temp_yaml_from_dictionary(dict_object):
    """Create a temporary file for the functions as a JSON file."""
    filename = mkstemp(suffix='.yaml')[1]
    with open(filename, 'w') as f:
        yaml.dump(dict_object, f)
    return filename

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