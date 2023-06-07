import json
from urllib.parse import urlparse

import requests
import yaml


CONNECTORS_FILE_PATH = 'airbyte_connectors.json'
AUTHENTICATION_COMPARISON_FILE_PATH = 'authentication_comparison.json'

def extract_connectors():
  with open(CONNECTORS_FILE_PATH) as f:
    connectors = json.load(f)
  
  lowcode_connectors = [connector for connector in connectors if connector.get('airbyte_status') == 'lowcode-connector']

  connector_info = []
  for connector in lowcode_connectors:
    base_url = connector.get('base_url', '')
    parsed_url = urlparse(base_url)

    connector_info.append({
        'name': connector.get('name', '').lower(),
        'domain': parsed_url.netloc
    })

  return connector_info


def find_authenticator_block(data):
    if isinstance(data, dict):
        if 'authenticator' in data:
            return data['authenticator']
        for key, value in data.items():
            auth_block = find_authenticator_block(value)
            if auth_block is not None:
                return auth_block
    elif isinstance(data, list):
        for item in data:
            auth_block = find_authenticator_block(item)
            if auth_block is not None:
                return auth_block
    return None


def get_authentication_from_yaml(connector_name):
    connector_name = connector_name.lower()

    connector_folder_name = connector_name.replace(" ", "-").replace("_", "-")
    connector_file_name = connector_folder_name.replace('-', '_')

    url = f"https://raw.githubusercontent.com/airbytehq/airbyte/master/airbyte-integrations/connectors/source-{connector_folder_name}/source_{connector_file_name}/manifest.yaml"

    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = yaml.safe_load(response.text)
            auth_block = find_authenticator_block(data)
            return auth_block if auth_block is not None else {}
        except Exception as e:
            return {}
    else:
        print(f'\nFailed to fetch file for {connector_name}, status code: {response.status_code}')
        return {}



if __name__ == "__main__":
    connectors = extract_connectors()
    auth_comparison = {}

    for connector in connectors:
        auth_block = get_authentication_from_yaml(connector['name'])
        auth_comparison[connector['name']] = auth_block
        print(f"\nFound authentication block for {connector['name']}") if auth_block != {} else print(f"\Could not found authentication block for {connector['name']}")

    with open(AUTHENTICATION_COMPARISON_FILE_PATH, 'w') as f:
        json.dump(auth_comparison, f, indent=2)
