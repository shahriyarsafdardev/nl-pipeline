from s3 import read_object, upload_object, list_objects
from urllib.parse import quote
from logger import getLogger
import json
import html2text

logger = getLogger()


def html_converter(text):
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    return converter.handle(text)


def create_md_files(filename):
	# Reading file from S3
	file_content = read_object(filename)
	connectors = json.loads(file_content)

	for connector in connectors:
		combined_file_content = ''

		page_count = connector.get('scraped_page_count', None)
		if not page_count:
			logger.info(f"No pages scrapped for {connector['name']}")
			continue

		logger.info(f"Creating md files for {connector['name']}")
		base_url = connector['base_url']
		quoted_base_url = quote(base_url, safe="")
		
		# getting the file keys for the connector
		file_keys = list_objects(file_name_filters=[(quoted_base_url, ".html")])

		for file_key in file_keys:
			# reading the html files and converting them to text
			file_content = html_converter(read_object(file_key, verbose=True))

			# saving that text to its md file
			upload_object(file_content, file_key.rsplit('.html', 1)[0] + ".md")

			# saving this content to the combined file
			combined_file_content += file_content + "\n"

		# uploading combined file to S3
		upload_object(combined_file_content, quoted_base_url + '-bulk' + '.md')

		# creating a new file with repetitions removed
		unique_paragraphs = set(combined_file_content.split("\n\n"))
		upload_object("\n\n".join(unique_paragraphs), quoted_base_url + '-bulk-concise' + '.md')


# Usage:
create_md_files('airbyte_connectors.json')
