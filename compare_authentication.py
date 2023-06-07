import json
import requests
import yaml
import pinecone
from urllib.parse import urlparse
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from config import settings


# Initialize Pinecone and OpenAI
pinecone.init(api_key=settings.pinecone_api_key, environment=settings.pinecone_env)
index_name = pinecone.Index(settings.pinecone_index_name)
ChatOpenAI.api_key = settings.openai_api_key
embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
llm = OpenAI(temperature=0, openai_api_key=settings.openai_api_key)
chain = load_qa_chain(llm, chain_type="stuff")


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


def get_base_url(domain):
    query = "What is the most likely base url. Some endpoints include a version like /0/, /v0/. Give me the url (including https://) and nothing else"
    response = get_langchain_response(domain, query)
  
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


def find_best_response(response, options):
    """Return the first matching response from the options, else 'None'."""
    response = response.lower()
    return next((option for option in options if option.lower() in response), 'None')


def get_langchain_response(domain, query):
    print(f'\nQuery: {query}')
    docsearch = Pinecone.from_existing_index(settings.pinecone_index_name, embeddings)
    docs = docsearch.similarity_search(query, k=5, filter={'page_urls': domain})
    response = chain.run(input_documents=docs, question=query)
    print(f'\nResponse: {response}')
    return response


def get_sphere_sub_auth_block(base_url, domain, authentication_type):
    if authentication_type == "BasicHttpAuthenticator":
        return {
            "type": "BasicHttpAuthenticator",
            "username": "{{config.username}}",
        }
    elif authentication_type == "BearerAuthenticator":
        return {
            "type": "BearerAuthenticator",
            "api_token": "{{config.auth_token}}",
        }
    elif authentication_type == 'ApiKeyAuthenticator':
        query = f"This {base_url} uses pagination to fetch data. What are the main parameters? If main parameters contain 'page' or 'offset' ignore them. Just get the main parameter's name and return only one word parameter"
        response = get_langchain_response(base_url, domain, query)
        return {
            'type': authentication_type,
            "api_token": "{{config.api_key}}",
            "header": response,
        }
    elif authentication_type == 'OAuth':
        query = f"Please generate a JSON which contains the following keys with the values for OAuth authentication for the URL {base_url}: 'client_id', 'client_secret', token_refresh_endpoint, refresh_token, access_token_name, expires_in_name. Give me the complete JSON and don't add extra text"
        response = get_langchain_response(domain, query)
        response = {'type': authentication_type}.update(response)
        return response
    else:
        return {'type': authentication_type}


def get_sphere_auth_block(connector):
    authenticator_options = [
        "BasicHttpAuthenticator",
        "BearerAuthenticator",
        "ApiKeyAuthenticator",
        "OAuth"
    ]
    base_url = get_base_url(connector['domain'])
    query = f"What is the method of authentication to authorize the API calls with this API? Following are the options: {authenticator_options}. Return the response from given options, just return the one word option. Return 'None' if don't find any"
    langchain_response = get_langchain_response(connector['domain'], query)
    authentication_type =  find_best_response(langchain_response, authenticator_options)
    response = get_sphere_sub_auth_block(base_url, connector['domain'], authentication_type)

    return response


def find_airbyte_auth_block(data):
    if isinstance(data, dict):
        if 'authenticator' in data:
            return data['authenticator']
        for key, value in data.items():
            auth_block = find_airbyte_auth_block(value)
            if auth_block is not None:
                return auth_block
    elif isinstance(data, list):
        for item in data:
            auth_block = find_airbyte_auth_block(item)
            if auth_block is not None:
                return auth_block
    return None


def get_airbyte_auth_block(connector_name):
    connector_name = connector_name.lower()

    connector_folder_name = connector_name.replace(" ", "-").replace("_", "-")
    connector_file_name = connector_folder_name.replace('-', '_')

    url = f"https://raw.githubusercontent.com/airbytehq/airbyte/master/airbyte-integrations/connectors/source-{connector_folder_name}/source_{connector_file_name}/manifest.yaml"

    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = yaml.safe_load(response.text)
            auth_block = find_airbyte_auth_block(data)
            return auth_block if auth_block is not None else {}
        except Exception as e:
            return {}
    else:
        print(f'\nFailed to fetch file for {connector_name}, status code: {response.status_code}')
        return {}


if __name__ == "__main__":
    connectors = extract_connectors()
    # connectors = [{'name': 'sendgrid', 'domain': 'docs.sendgrid.com'},  {'name': 'sentry', 'domain': 'docs.sentry.io'}, {'name': 'quickbooks', 'domain': 'developer.intuit.com'}]
    auth_comparison = {}

    for connector in connectors:
        airbyte_auth_block = get_airbyte_auth_block(connector['name'])
        sphere_auth_block = get_sphere_auth_block(connector)
        auth_comparison[connector['name']] = {
            'sphere_auth_block': sphere_auth_block,
            'airbyte_auth_block': airbyte_auth_block
        }
        print(f"\nProcessed connector: {connector['name']}")

    with open(AUTHENTICATION_COMPARISON_FILE_PATH, 'w') as f:
        json.dump(auth_comparison, f, indent=4)
