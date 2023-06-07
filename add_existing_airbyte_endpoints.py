import json
import requests
import yaml
import io
from logger import getLogger
from s3 import read_object, upload_object

logger = getLogger()

def get_paths_and_url_base_from_yaml(yaml_data):
    """
    Recursively traverses the YAML data to find 'path' and 'url_base' attributes.

    Args:
        yaml_data (dict or list): YAML data structure.

    Returns:
        path_list (list): List of 'path' attributes.
        url_base (str or None): 'url_base' attribute value.
    """
    path_list = []
    url_base = None

    if isinstance(yaml_data, dict):
        for key, value in yaml_data.items():
            if key == 'path':
                path_list.append(value)
            elif key == 'url_base':
                url_base = value
            elif isinstance(value, (dict, list)):
                paths, url_base_value = get_paths_and_url_base_from_yaml(value)
                path_list.extend(paths)
                if url_base is None and url_base_value is not None:
                    url_base = url_base_value
    elif isinstance(yaml_data, list):
        for item in yaml_data:
            paths, url_base_value = get_paths_and_url_base_from_yaml(item)
            path_list.extend(paths)
            if url_base is None and url_base_value is not None:
                url_base = url_base_value

    return path_list, url_base


def find_manifest_file(connector_name):
    """
    Fetches the YAML manifest file for a given connector and extracts 'path' attributes and 'url_base'.

    Args:
        connector_name (str): Name of the connector.

    Returns:
        paths_list (list): List of 'path' attributes.
        url_base (str or None): 'url_base' attribute value.
    """
    # Convert the name into lowercase
    connector_name = connector_name.lower()

    # Replace the spaces with hyphens and underscores respectively
    connector_folder_name = connector_name.replace(" ", "-").replace("_", "-")
    connector_file_name = connector_folder_name.replace('-', '_')

    url = f"https://raw.githubusercontent.com/airbytehq/airbyte/master/airbyte-integrations/connectors/source-{connector_folder_name}/source_{connector_file_name}/manifest.yaml"

    # Fetch the content of the file
    response = requests.get(url)

    # Check to ensure the request was successful
    if response.status_code == 200:
        # Parse YAML data and extract paths and url_base
        yaml_data = yaml.safe_load(response.text)
        paths_list, url_base = get_paths_and_url_base_from_yaml(yaml_data)

        # filter paths that are of type string
        return [path for path in paths_list if type(path) == str], url_base
    else:
        print(f'Failed to fetch file, status code: {response.status_code}')
        return None, None


def add_existing_airbyte_endpoints(filename, local=False, connector_type='lowcode-connector'):
    if local:
        # Reading file from local storage
        with open(filename, 'r') as f:
            connectors = json.load(f)
    else:
        # Reading file from S3
        file_content = read_object(filename)
        connectors = json.loads(file_content)

    for connector in connectors:
        if connector['airbyte_status'] != connector_type:
            logger.info(f"Skipping {connector['name']} because it is not a {connector_type}")
            continue

        # read the endpoints from the manifest file
        urls, api_base_url = find_manifest_file(connector['name'])

        if not urls or not api_base_url:
            logger.info(f"No Airbyte endpoints found for {connector['name']}")
            connector['existing_airbyte_endpoints'] = []
            continue

        logger.info(f"Fetched URLs for {connector['name']}")

        # update the connectors list
        connector['existing_airbyte_endpoints'] = urls
        
        # write to file
        if local:
            # Saving file to local storage
            with open(filename, 'w') as f:
                json.dump(connectors, f, indent=4)
        else:
            # Saving file to S3
            updated_connectors = json.dumps(connectors, indent=4)
            file_obj = io.BytesIO(updated_connectors.encode('utf-8'))
            upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})


add_existing_airbyte_endpoints('airbyte_connectors.json', local=True, connector_type='lowcode-connector')