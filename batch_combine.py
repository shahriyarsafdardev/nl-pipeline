from s3 import read_object, upload_object, list_objects
from urllib.parse import quote
from logger import getLogger
import json
from scraper import html_converter

logger = getLogger()


def create_md_files(filename):
	# Reading file from S3
	file_content = read_object(filename)
	connectors = json.loads(file_content)

	for connector in connectors:
		page_count = connector.get('scraped_page_count', None)
		if not page_count:
			logger.info(f"No pages scrapped for {connector['name']}")
			continue

		logger.info(f"Creating md files for {connector['name']}")
		base_url = connector['base_url']
		
		# getting the file keys for the connector
		file_keys = list_objects(file_name_filters=[(quote(base_url, safe=""), ".html")])

		for file_key in file_keys:
			# reading the html files and converting them to text
			file_content = html_converter(read_object(file_key, verbose=True))

			# saving that text to its md file
			upload_object(file_content, file_key.rsplit('.html', 1)[0] + ".md")

			# saving this content to the combined file

		# creating a new file with repetitions removed






		


# Usage:
create_md_files('airbyte_connectors.json')
