from urllib.parse import quote
from s3 import read_object, upload_object, list_objects
from logger import getLogger
from pinecone_db import store_chunks
import json
from embedding_helper import split_into_chunks, text_slice_to_vector

logger = getLogger()


def create_embeddings(filename):
	# Reading file from S3
	file_content = read_object(filename)
	connectors = json.loads(file_content)

	for connector in connectors:
		# reading the concise bulk file
		quoted_base_url = quote(connector['base_url'], safe="")
		concise_bulk_file = read_object(quoted_base_url + '-bulk-concise' + '.md')

		# generating chunks and storing to pinecone
		chunks = split_into_chunks(concise_bulk_file)
		chunks = [text_slice_to_vector(chunk, connector['base_url']) for chunk in chunks]
		store_chunks(chunks)
		

create_embeddings('airbyte_connectors.json')

