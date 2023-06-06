from urllib.parse import quote
from s3 import read_object, upload_object
import json
import re
from logger import getLogger
import io

link_pattern = r'\s(https?://[^\s]+|/[^\s]+)'
logger = getLogger()


import requests
import yaml


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

        return paths_list, url_base
    else:
        print(f'Failed to fetch file, status code: {response.status_code}')
        return None, None


def extract_urls_from_concise_bulk(filename):
	# read the contents of the connectors file
	file_content = read_object(filename)
	connectors = json.loads(file_content)

	upload_object('Comparison between Airbyte connector endpoints and our concise file endpoints\n\n', 'airbyte_connectors_comparison.txt')

	for connector in connectors:
		airbyte_status =  connector.get('airbyte_status', None)
		if airbyte_status == 'lowcode-connector':
			logger.info(f"Comparing {connector['name']}")

			# get the existing comparion list so we can append to it
			comparison_list = read_object('airbyte_connectors_comparison.txt')
			
			# if this is an airbyte low code connector, extract urls from concise bulk file
			quoted_base_url = quote(connector['base_url'], safe="")
			concise_bulk_file = read_object(f"{quoted_base_url}-bulk-concise.md")

			# find all urls from concise file and airbyte connector manifest then remove api base url and leading / 
			airbyte_connector_urls, api_base_url = find_manifest_file(connector['name'])

			# if no data found from Airbyte, move onto next connector
			if not airbyte_connector_urls or not api_base_url:
				logger.info(f"No Airbyte endpoints found for {connector['name']}")
				continue


			airbyte_connector_urls = [url.replace(api_base_url, '').lstrip('/') for url in airbyte_connector_urls]
			concise_file_urls = re.findall(link_pattern, concise_bulk_file)
			concise_file_urls = [url.replace(api_base_url, '').lstrip('/') for url in concise_file_urls]

			# urls that exist in both
			common_urls = set(concise_file_urls) & set(airbyte_connector_urls)

			# urls in the airbyte connector but not in the concise file
			urls_in_airbyte_connector = set(airbyte_connector_urls) - set(concise_file_urls) 	

			# update the comparison list and upload to S3
			comparison_list += f"{connector['name']}:\nCommon endpoints: {common_urls}\nEndpoints in Airbyte only: {urls_in_airbyte_connector}\n\n"
			upload_object(io.BytesIO(comparison_list.encode('utf-8')), 'airbyte_connectors_comparison.txt')
			logger.info(f"Updated list for {connector['name']}")


extract_urls_from_concise_bulk('airbyte_connectors.json')

