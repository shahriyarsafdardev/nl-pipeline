import json
import pinecone

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain

from config import settings


# Initialize Pinecone and OpenAI
pinecone.init(api_key=settings.pinecone_api_key,
              environment=settings.pinecone_env)
index_name = pinecone.Index(settings.pinecone_index_name)
ChatOpenAI.api_key = settings.openai_api_key
embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
llm = OpenAI(temperature=0, openai_api_key=settings.openai_api_key)
chain = load_qa_chain(llm, chain_type="stuff")

OUTPUT_FILE = "transformations_output.json"


def load_config(config_file):
    """Load the transformations config file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except IOError as e:
        print(f"Unable to open the config file: {e}")
        return None


def save_output(output):
    """Save the output JSON file."""
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(output, f, indent=4)
    except IOError as e:
        print(f"Unable to write to the output file: {e}")


def extract_base_url_part(url):
    if '/v1' in url:
        return url.split('/v1')[0] + '/v1'
    elif '/v2' in url:
        return url.split('/v2')[0] + '/v2'
    elif '/v3' in url:
        return url.split('/v3')[0] + '/v3'
    elif '/api' in url:
        return url.split('/api')[0] + '/api'
    elif '.com' in url:
        return url.split('.com')[0] + '.com'
    else:
        return url


def find_best_response(response, options):
    """Return the first matching response from the options, else 'None'."""
    response = response.lower()
    return next((option for option in options if option.lower() in response), 'None')


def get_langchain_response(domain_base_url, key, query):
    if key != 'base_url':
        query = replace_base_url(query)
    print(f'\nQuery: {query}')
    docsearch = Pinecone.from_existing_index(settings.pinecone_index_name, embeddings)
    docs = docsearch.similarity_search(query, k=5, filter={'domain_base_url': domain_base_url})
    print(f'\nDocs: {docs}')
    response = chain.run(input_documents=docs, question=query)
    if key == 'base_url':
        response = extract_base_url_part(response)
    print(f'\nResponse: {response}')
    return response


def replace_base_url(query):
    base_url = load_config('transformations_output.json').get('base_url')
    return query.replace("{base_url}", base_url)


def get_authentication_sub_object(domain_base_url, authentication_object, authentication_type, key):
    query = ''
    if authentication_type == 'ApiKeyAuthenticator':
        query = authentication_object['api_authentication_header']['description']
        response = get_langchain_response(domain_base_url, key, query)
        return {
            'type': authentication_type,
            'api_authentication_header': response
        }
    elif authentication_type == 'OAuth':
        query = authentication_object['oauth_authentication_object']['description']
        response = get_langchain_response(domain_base_url, key, query)
        return {
            'type': authentication_type,
            'oauth_authentication_object': response
        }


def get_pagination_sub_object(domain_base_url, pagination_object, pagination_type, key):
    query = ''
    if pagination_type == 'OffsetIncrement' or pagination_type == 'PageIncrement':
        query = pagination_object['increment_pagination_parameter']['description']
        response = get_langchain_response(domain_base_url, key, query)
        return {
            'type': pagination_type,
            'increment_pagination_parameter': response
        }
    elif pagination_type == 'CursorPagination':
        query = pagination_object['cursor_pagination_value']['description']
        response = get_langchain_response(domain_base_url, key, query)
        return {
            'type': pagination_type,
            'cursor_pagination_value': response
        }


def query_with_langchain(domain_base_url, key, query_object):
    """Query the vector database for the given domain_base_url and key using LangChain."""
    sub_query = f"Following are the options: {query_object['options']}. Return the response from given options, just return the one word option." if 'options' in query_object else "Return 'None' if don't find any"
    query = f"{query_object['description']}. {sub_query}"
    langchain_response = get_langchain_response(domain_base_url, key, query)
    best_response =  find_best_response(langchain_response, query_object['options']) if 'options' in query_object else langchain_response
    if key == 'authentication':
        response = get_authentication_sub_object(domain_base_url, query_object, best_response, key)
        return response if response is not None else best_response
    elif key == 'pagination':
        response = get_pagination_sub_object(domain_base_url, query_object, best_response, key)
        return response if response is not None else best_response
    return best_response.strip()


def infer_properties(domain_base_url, config_file):
    """Infer the properties about a domain_base_url and save the output JSON file."""
    config = load_config(config_file)
    output = {}
    if config is not None:
        for key in config.keys():
            value = query_with_langchain(domain_base_url, key, config[key])
            output[key] = value
        save_output(output)


if __name__ == "__main__":
    infer_properties(
        "https://docs.sendgrid.com/api-reference", "transformations_config.json")
