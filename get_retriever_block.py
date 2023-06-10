import json
from urllib.parse import urlparse
import requests
import yaml
import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from logger import getLogger
from s3 import read_object
from config import settings


# Initialize Pinecone and OpenAI
pinecone.init(api_key=settings.pinecone_api_key,
              environment=settings.pinecone_env)
index_name = pinecone.Index(settings.pinecone_index_name)
ChatOpenAI.api_key = settings.openai_api_key
embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
llm = OpenAI(temperature=0, openai_api_key=settings.openai_api_key)
chain = load_qa_chain(llm, chain_type="stuff")

logger = getLogger()


# Function to load JSON data from a file
def load_json_from_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)


# Function to load JSON data from S3
def load_json_from_s3(filename):
    file_content = read_object(filename)
    if file_content is None:
        return []
    return json.loads(file_content)


# Function to find the base URL given the domain base URL
def get_base_url(domain_base_url):
    query = "What is the most likely base url. Some endpoints include a version like /0/, /v0/. Give me the url (including https://) and nothing else"
    response = get_langchain_response(domain_base_url, query)

    if '/v1' in response:
        return response.split('/v1')[0] + '/v1'
    elif '/v2' in response:
        return response.split('/v2')[0] + '/v2'
    elif '/v3' in response:
        return response.split('/v3')[0] + '/v3'
    elif '/api' in response:
        return response.split('/api')[0] + '/api'
    elif '.com' in response:
        return response.split('.com')[0] + '.com'
    else:
        return response


# Function to find the best matching response from the options
def find_best_response(response, options):
    """Return the first matching response from the options, else 'None'."""
    response = response.lower()
    return next((option for option in options if option.lower() in response), 'None')


# Function to get the response from langchain for a given query
def get_langchain_response(domain_base_url, query):
    logger.info('Query: {}'.format(query))
    docsearch = Pinecone.from_existing_index(
        settings.pinecone_index_name, embeddings)
    docs = docsearch.similarity_search(
        query, k=5, filter={'domain_base_url': domain_base_url})
    response = chain.run(input_documents=docs, question=query)
    logger.info('Response: {}'.format(response))
    return response


# Function to identify the pagination strategy from the pagination response
def get_pagination_strategy(pagination_response):
    if any(element in pagination_response for element in ['offset', 'limit']):
        return {
            "pagination_strategy": {"type": "OffsetIncrement", "page_size": 5},
            "page_token_option": {"field_name": "offset"},
        }
    elif any(element in pagination_response for element in ['page', 'page_size', 'pagesize', 'per_page', 'page_number', 'page number', 'pagenum']):
        return {
            "pagination_strategy": {"type": "PageIncrement", "page_size": 5},
            "page_size_option": {"field_name": "page_size"},
            "page_token_option": {"field_name": "page"},
        }
    elif any(element in pagination_response for element in ['cursor', 'link', 'next_token']):
        return {
            "pagination_strategy": {"type": "CursorPagination"},
            "page_token_option": {"field_name": "from"},
        }
    return {}


# Function to get the pagination parameters for a base URL and domain
def get_pagination_parameters(base_url, domain):
    try:
        pagination_params_query = (
            f"This {base_url} uses pagination to fetch data. What are the main parameters? If main parameters contain 'page' or 'offset' ignore them"
            f"Just get the main parameter's name and return only one word parameter"
        )
        pagination_response = get_langchain_response(
            domain, pagination_params_query)
        if pagination_response and "none" not in pagination_response.lower():
            return {"page_size_option": {
                "type": "RequestOption",
                "inject_into": "request_parameter",
                "field_name": pagination_response
            }}
        return {}
    except (ValueError, KeyError, Exception) as e:
        print(
            f"An error occurred while retrieving pagination parameters: {str(e)}")
        return {}


# Function to get the cursor pagination value from the cursor value response
def get_cursor_pagination_value(cursor_value_response):
    cursor_values = {
        "link": "{{headers.link.next.cursor}}",
        "cursor": "{{headers.link.next.cursor}}",
        "url": "{{headers['urls']['next']}}",
        "last record id": "{{last_records[-1]['id']}}",
    }
    return next((v for k, v in cursor_values.items() if k in cursor_value_response.lower()), "")


# Function to predict the sub retriever block given a base URL and domain
def predict_sub_retriever_block(base_url, domain):
    try:
        pagination_query = (
            f"What is the pagination strategy used for the URL {base_url} to fetch the data."
            f"The pagination strategy can be cursor pagination, page increment pagination, offset increment pagination?."
            f"Don't add any extra text, just tell pagination strategy being used in aginator of retriever block"
        )
        pagination_response = get_langchain_response(domain, pagination_query)
        paginator_json = {
            "type": "DefaultPaginator",

            "pagination_strategy": {"type": ""},
            "page_token_option": {
                "type": "RequestOption",
                "inject_into": "request_parameter",
                "field_name": "",
            },
        }
        pagination_strategy = get_pagination_strategy(pagination_response.lower())

        if pagination_strategy is None:
            return {"type": "NoPagination"}

        paginator_json["pagination_strategy"].update(
            pagination_strategy["pagination_strategy"])
        paginator_json["page_token_option"].update(
            pagination_strategy["page_token_option"])

        strategy_type = pagination_strategy["pagination_strategy"]["type"]
        if strategy_type in ["OffsetIncrement", "PageIncrement"]:
            paginator_json.update(
                get_pagination_parameters(base_url, domain))

        if strategy_type == "CursorPagination":
            cursor_value_query = (
                f"This url {base_url} uses cursor pagination."
                f"I want to know, On what basis it makes further request to fetch the next data"
                f"either it uses next url in headers, last record id in parameter or next cursor link?"
                f"Just tell me the method it uses and don't add extra text"
            )
            cursor_value_response = get_langchain_response(
                domain, cursor_value_query)
            paginator_json["pagination_strategy"]["cursor_value"] = get_cursor_pagination_value(
                cursor_value_response)

        return paginator_json
    except Exception as e:
        logger.error(
            f"Something went wrong while getting pagination type: {e}")
        return {"type": "NoPagination"}


# Function to extract the sphere retriever block given a connector
def extract_sphere_retriever_block(connector):
    base_url = (connector['base_url']).strip()

    domain = urlparse(base_url).netloc

    pagination_object = predict_sub_retriever_block(base_url, domain)
    retriever_block = {
        "type": "SimpleRetriever",
                "record_selector": {"$ref": "#/definitions/selector"},
                "paginator": pagination_object,
                "requester": {"$ref": "#/definitions/requester"}
    }
    return retriever_block


# Recursive function to find the retriever block in the Airbyte JSON data
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


# Function to extract the Airbyte retriever block given a connector name
def extract_airbyte_retriever_block(connector_name):
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
        logger.error('\nFailed to fetch file for {}, status code: {}'.format(
            connector_name, response.status_code))
        return {}


# Function to flatten a json object for comparison
def json_flatten(json_object, delimiter="."):
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + delimiter)
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + delimiter)
                i += 1
        else:
            out[name[:-1]] = x

    flatten(json_object)
    return out


# Function to calculate the similarity percentage between two JSON blocks
def calculate_line_similarity(airbyte_block, sphere_block):

    # Flattening json objects and getting key-value pairs
    airbyte_block_key_value_pair = list(json_flatten(airbyte_block).items())
    sphere_block_key_value_pair = list(json_flatten(sphere_block).items())

    # Counting matches
    matches = len(set(airbyte_block_key_value_pair).intersection(
        sphere_block_key_value_pair))
    similarity = (matches / len(airbyte_block_key_value_pair)) * \
        100 if len(airbyte_block_key_value_pair) != 0 else matches
    return round(similarity, 2), matches, len(airbyte_block_key_value_pair)


# Main function to process connectors and calculate the retriever block similarities
def main(filename, local=False):
    connectors = load_json_from_file(
        filename) if local else load_json_from_s3(filename)

    retrievers_comparison = {}
    total_matches = 0
    total_airbyte_block_pair_count = 0

    for connector in connectors:
        if connector.get('airbyte_status') != 'lowcode-connector':
            continue

        airbyte_retriever_block = extract_airbyte_retriever_block(
            connector['name'])
        sphere_retriever_block = extract_sphere_retriever_block(connector)
        retriever_block_similarity, matches_count, airbyte_block_pair_count = calculate_line_similarity(
            airbyte_retriever_block, sphere_retriever_block)
        total_matches = total_matches + matches_count
        total_airbyte_block_pair_count = total_airbyte_block_pair_count + \
            airbyte_block_pair_count
        retrievers_comparison[connector['name']] = {
            'airbyte_retriever_block': airbyte_retriever_block,
            'sphere_retriever_block': sphere_retriever_block,
            'similarity': retriever_block_similarity
        }

        logger.info("Processed connector: {}".format(connector['name']))

    overall_similarity = (total_matches/total_airbyte_block_pair_count) * \
        100 if total_airbyte_block_pair_count != 0 else total_matches

    with open('connectors_retriever_blocks.json', 'w') as f:
        json.dump({"overall_similarity": round(overall_similarity, 2),
                  "retrievers": retrievers_comparison}, f, indent=4)


if __name__ == "__main__":
    main('airbyte_connectors.json', local=True)
