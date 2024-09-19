import json
import os

from ba_web_app.ai_experiments.models import AiExperiment
from ba_web_app.ai_utils.client import get_ai_responses, submit_experiment


def get_potential_aliases_for_pub(pub_id):
    """Run a one-off script to match antibodies to aliases."""
    sql = """
    copy (
    select atb_zdb_id, atb_type, atb_hviso_name, atb_immun_organism, atb_host_organism, string_agg(dalias_alias, ' ; ') as aliases 
    from 
    (
        SELECT
            recattrib_source_zdb_id AS pub,
                    antibody.atb_zdb_id, atb_type, atb_hviso_name, atb_immun_organism, atb_host_organism,
                    data_alias.dalias_alias
        FROM
            record_attribution
                    left join antibody on recattrib_data_zdb_id = atb_zdb_id
                    left join data_alias on recattrib_data_zdb_id = dalias_data_zdb_id
        WHERE
                    recattrib_source_zdb_id = '{pub_id}'
                    and get_obj_type(recattrib_data_zdb_id) = 'ATB'
    ) as subq
    group by atb_zdb_id, atb_type, atb_hviso_name, atb_immun_organism, atb_host_organism
    ) to stdout with csv
    """
    sql = sql.format(pub_id=pub_id)

    compact_sql = " ".join(sql.split("\n"))
    cmd_template = "psql -h db zfindb"
    cmd = f"echo \"{compact_sql}\" | {cmd_template}"
    result = os.popen(cmd)
    results = result.read()
    header = "atb_zdb_id,atb_type,atb_hviso_name,atb_immun_organism,atb_host_organism,aliases\n"
    return header + results

def match_all_experiments(flask_app):
    upload_folder = flask_app.config["UPLOAD_FOLDER"]
    # experiment_ids = [359, 360, 361, 362, 363, 364, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
    # experiment_ids = [476, 477]
    experiment_ids = [419, 413, 410, 370, 363]
    for experiment_id in experiment_ids:
        ai_experiment = AiExperiment.query.get(experiment_id)
        responses = get_ai_responses(ai_experiment)
        print(f"Experiment ID: {experiment_id}")
        for pub_id, pub_response in responses.items():
            # should only be one
            pub_id = pub_id.replace(".pdf", "")
            potential_aliases = get_potential_aliases_for_pub(pub_id)
            prompt = prompt_for_matching(pub_response, potential_aliases)
            ai_func = ai_function_string()

            #make directory in storage area for experiment
            storage_directory = os.path.join(upload_folder, "match-" + str(experiment_id))
            if not os.path.exists(storage_directory):
                os.makedirs(storage_directory)

            #write prompt to file
            prompt_file_path = os.path.join(storage_directory, pub_id + "_prompt.txt")
            with open(prompt_file_path, "w") as f:
                f.write(prompt)

            #write ai function to file
            ai_func_file_path = os.path.join(storage_directory, pub_id + "_ai_func.json")
            with open(ai_func_file_path, "w") as f:
                f.write(ai_func)

            #write potential aliases to file
            potential_aliases_file_path = os.path.join(storage_directory, pub_id + "_potential_aliases.csv")
            with open(potential_aliases_file_path, "w") as f:
                f.write(potential_aliases)

            #write pub response to file
            pub_response_file_path = os.path.join(storage_directory, pub_id + "_pub_response.json")
            with open(pub_response_file_path, "w") as f:
                f.write(pub_response)

            #write pub id to file
            pub_id_file_path = os.path.join(storage_directory, "pub_id.txt")
            with open(pub_id_file_path, "w") as f:
                f.write(pub_id)

            #write experiment id to file
            experiment_id_file_path = os.path.join(storage_directory, "experiment_id.txt")
            with open(experiment_id_file_path, "w") as f:
                f.write(str(experiment_id))

            submit_experiment(api_key=flask_app.config["OPENAI_API_KEY"],
                                  assistant_instructions=get_assistant_definition(),
                                  prompt=prompt,
                                  functions=ai_func,
                                  files=[],
                                  unique_id="match-" + str(experiment_id))

            break


def prompt_for_matching(previous_response, potential_aliases):
    prompt_template = """
You previously gave me this list of antibodies (name, supplier, catalog number, other identifiers) with one entry per line that you detected in a publication.
Now I need to map them to their corresponding IDs. Here is the list of antibodies you provided me with:

```
%previous_response%
```

Here is a list of identifiers that might be matches (though they could also not be matches):
```
%potential_aliases%
```

Please provide me with a list of the antibodies you provided earlier, along with their corresponding atb_zdb_id. If an antibody does not have a corresponding identifier, please indicate that with "N/A".

Example:
```
{"match_antibodies":
[
{"name": "anti-fasn (cell signaling technology; 3180s)", "atb_zdb_id": "N/A"},
{"name": "anti-gapdh (cell signaling technology; 2118s)", "atb_zdb_id": "ZDB-ATB-140115-2"},
...
]
}
```
    """
    prompt = prompt_template.replace("%previous_response%", previous_response)
    prompt = prompt.replace("%potential_aliases%", potential_aliases)
    return prompt

def ai_function_string():
    return """
[
  {
    "type": "function",
    "function": {
      "name": "match_antibodies",
      "description": "Report discovered matches for antibodies to their IDs",
      "parameters": {
        "type": "object",
        "properties": {
          "match_data": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string",
                  "description": "The name of the identified antibody"
                },
                "atb_zdb_id": {
                  "type": "string",
                  "description": "The ID of the antibody in ZFIN or 'N/A' if not found"
                }
              },
              "required": ["name", "atb_zdb_id"]
            }
          }
        },
        "required": ["match_data"]
      }
    }
  }
]
    """

def get_assistant_definition():
    return """
    You are a biocurator with special knowledge of antibodies. You will use your antibody knowledge and given aliases to make matches between lists of antibodies to their official ZDB IDs.    
    Use the match_antibodies tool to report the matches.
    """

def combine_prompts(flask_app):
    """Combine all prompts into one file."""
    upload_folder = flask_app.config["UPLOAD_FOLDER"]

    #get all subdirs in upload folder matching the name "match-*"
    subdirs = [d for d in os.listdir(upload_folder) if os.path.isdir(os.path.join(upload_folder, d)) and d.startswith("match-")]

    #read all prompt files (_prompt.txt) in each subdir
    final_mappings = {}
    subdirs.sort()
    for subdir in subdirs:
        prompt_file = os.path.join(upload_folder, subdir, "_prompt.txt")
        with open(prompt_file, "r") as f:
            prompt_text = f.read()
            try:
                prompt_json = json.loads(prompt_text)
                keylist = [k for k in prompt_json.keys()]
                firstkey = keylist[0]
                for match in prompt_json[firstkey]:
                    if match["atb_zdb_id"] != "N/A":
                        if match["name"] in final_mappings:
                            if final_mappings[match["name"]] != match["atb_zdb_id"]:
                                print(f"Contradicting match for {match['name']}: {match['atb_zdb_id']} and {final_mappings[match['name']]}")
                        final_mappings[match["name"]] = match["atb_zdb_id"]
            except:
                pass
    return final_mappings
