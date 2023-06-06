from s3 import read_object, upload_object, list_objects
from urllib.parse import quote
from logger import getLogger
import json
import html2text
import re
import io

logger = getLogger()

link_pattern = r'\s(https?://[^\s]+|/[^\s]+)'

def html_to_md_converter(text):
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.body_width = 0
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
		file_keys = list_objects([quoted_base_url, ".html"])
		logger.info(f"Extracted {len(file_keys)} file keys for {connector['name']}")

		for file_key in file_keys:
			# reading the html files and converting them to text

			logger.info(f"Generating .md file for {file_key}")
			file_content = html_to_md_converter(read_object(file_key))
			logger.info(f"Generating .md file for {file_key}")

			# saving that text to its md file
			upload_object(io.BytesIO(file_content.encode('utf-8')), file_key.rsplit('.html', 1)[0] + ".md")

			# saving this content to the combined file
			combined_file_content += file_content + "\n"

		# uploading combined file to S3
		upload_object(io.BytesIO(combined_file_content.encode('utf-8')), quoted_base_url + '-bulk' + '.md')
		logger.info(f"Bulk file uploaded for {connector['name']}")

		# creating a new file with repetitions removed
		unique_paragraphs = set(combined_file_content.split("\n\n"))
		upload_object(io.BytesIO("\n\n".join(unique_paragraphs).encode('utf-8')), quoted_base_url + '-bulk-concise' + '.md')
		logger.info(f"Concise bulk file uploaded for {connector['name']}")


		# extracting unique urls from the bulk-concise
		logger.info(f"Extracting links for {connector['name']}")
		extracted_links = []
		for paragraph in unique_paragraphs:
			matches = re.findall(link_pattern, paragraph)
			extracted_links.extend(matches)

		# adding the endpoint_count field to the connector object and uploading to S3
		connector['endpoint_count'] = len(list(set(extracted_links)))
		logger.info(f"Extracted {len(extracted_links)} links for {connector['name']}: {extracted_links}")

		updated_connectors = json.dumps(connectors, indent=4)
		file_obj = io.BytesIO(updated_connectors.encode('utf-8'))
		upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})


# Usage:
create_md_files('airbyte_connectors.json')
