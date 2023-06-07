import json


CONNECTORS_FILE_PATH = 'airbyte_connectors.json'

def extract_connectors():
  with open(CONNECTORS_FILE_PATH) as f:
    connectors = json.load(f)
  lowcode_connectors = [connector for connector in connectors if connector.get('airbyte_status') == 'lowcode-connector']
  return lowcode_connectors


if __name__ == "__main__":
  connectors = extract_connectors()
