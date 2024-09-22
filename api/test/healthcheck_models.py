import json
from pathlib import Path
import requests
from huggingface_hub import hf_hub_url
import pytest


def load_model_data(file_path):
    """Load model data from a JSON file.

    This function opens a specified JSON file and loads its contents into a
    Python object. It uses the built-in `json` module to parse the file,
    which should contain valid JSON data. The function assumes that the file
    exists and is readable.

    Args:
        file_path (str): The path to the JSON file containing model data.

    Returns:
        dict: The contents of the JSON file as a Python dictionary.
    """

    with open(file_path, "r") as models_file:
        return json.load(models_file)


def flatten_model_data(families):
    """Flatten model data from a list of families.

    This generator function iterates through a list of family dictionaries,
    extracting the repository name and filenames from each model within the
    families. It yields a tuple containing the repository name and the
    corresponding filename for each file in the models.

    Args:
        families (list): A list of dictionaries, where each dictionary represents
            a family containing models and their associated files.

    Yields:
        tuple: A tuple containing the repository name and the filename for each
            file in the models.
    """

    for family in families:
        for model in family["models"]:
            for file in model["files"]:
                yield model["repo"], file["filename"]


def check_model_availability(repo, filename):
    """Check the availability of a model file in a specified repository.

    This function constructs a URL for the specified model file in the given
    repository and sends a HEAD request to check if the file is accessible.
    It returns True if the file is available and False otherwise.

    Args:
        repo (str): The name of the repository where the model is stored.
        filename (str): The name of the model file to check for availability.

    Returns:
        bool: True if the model file is available, False otherwise.
    """

    url = hf_hub_url(repo, filename, repo_type="model", revision="main")
    response = requests.head(url)
    if response.ok:
        return True
    else:
        return False


test_dir = Path(__file__).parent
model_data = load_model_data(test_dir.parent / "src/serge/data/models.json")
checks = list(flatten_model_data(model_data))


@pytest.mark.parametrize("repo,filename", checks)
def test_model_available(repo, filename):
    assert check_model_availability(repo, filename), f"Model {repo}/{filename} not available"
