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


def find_best_response(response, options):
    """Return the first matching response from the options, else 'None'."""
    response = response.lower()
    return next((option for option in options if option.lower() in response), 'None')


def query_with_langchain(domain, query_object):
    """Query the vector database for the given domain and key using LangChain."""
    query = f"{query_object['description']}. Following are the options: {query_object['options']}. Return the response from given options, just return the one word option."
    docsearch = Pinecone.from_existing_index(settings.pinecone_index_name, embeddings)
    docs = docsearch.similarity_search(query, k=5, filter={'page_urls': domain})
    response = chain.run(input_documents=docs, question=query)
    print(f'\nQuery: {query}\n\nResponse: {response}')
    return find_best_response(response, query_object['options'])


def infer_properties(domain, config_file):
    """Infer the properties about a domain and save the output JSON file."""
    config = load_config(config_file)
    output = {}
    if config is not None:
        for key in config.keys():
            value = query_with_langchain(domain, config[key])
            output[key] = value
        save_output(output)


if __name__ == "__main__":
    infer_properties(
        "docs.sendgrid.com", "transformations_config.json")
