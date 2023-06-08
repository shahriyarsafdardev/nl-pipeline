import json
import requests
import yaml
import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from config import settings
from logger import getLogger
from s3 import read_object

logger = getLogger()


def load_json_from_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)


def load_json_from_s3(filename):
    file_content = read_object(filename)
    if file_content is None:
        return []
    return json.loads(file_content)


def find_airbyte_retriever_block(data):
    if isinstance(data, dict):
        if 'retriever' in data:
            return data['retriever']
        for key, value in data.items():
            retriever_block = find_airbyte_retriever_block(value)
            if retriever_block is not None:
                return retriever_block
    elif isinstance(data, list):
        for item in data:
            retriever_block = find_airbyte_retriever_block(item)
            if retriever_block is not None:
                return retriever_block
    return None


def get_airbyte_retriever_block(connector_name):
    connector_name = connector_name.lower()

    connector_folder_name = connector_name.replace(" ", "-").replace("_", "-")
    connector_file_name = connector_folder_name.replace('-', '_')

    url = f"https://raw.githubusercontent.com/airbytehq/airbyte/master/airbyte-integrations/connectors/source-{connector_folder_name}/source_{connector_file_name}/manifest.yaml"

    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = yaml.safe_load(response.text)
            retriever_block = find_airbyte_retriever_block(data)
            return retriever_block if retriever_block is not None else {}
        except Exception as e:
            return {}
    else:
        logger.error("Failed to fetch file for {}, status code: {}".format(connector_name, response.status_code))
        return {}


def main(filename, local=False):
    connectors = load_json_from_file(filename) if local else load_json_from_s3(filename)
    retriever_blocks = {}

    for connector in connectors:
        if connector.get('airbyte_status') != 'lowcode-connector':
            continue
        airbyte_retriever_block = get_airbyte_retriever_block(connector['name'])
        retriever_blocks[f"{connector['name'].lower()}_retriever"] = airbyte_retriever_block
        logger.info("Processed connector: {}".format(connector['name']))

    with open('connectors_retriever_blocks.json', 'w') as f:
        json.dump(retriever_blocks, f, indent=4)


if __name__ == "__main__":
    main('airbyte_connectors.json', local=True)
