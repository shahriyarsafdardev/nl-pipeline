from s3 import read_object, upload_object, list_objects
from urllib.parse import quote
from logger import getLogger
import json
import html2text
import re
import io
from link_matcher import detect_links
from termcolor import colored

logger = getLogger()

def convert_html_to_md(text):
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(text)

def create_md_files(filename, local=False):
    if local:
        with open(filename, 'r') as f:
            connectors = json.load(f)
    else:
        file_content = read_object(filename)
        connectors = json.loads(file_content)

    for connector in connectors:
        page_count = connector.get('scraped_page_count', None)
        if not page_count or connector['airbyte_status'] != 'lowcode-connector':
            logger.info("No pages scrapped for {}".format(connector['name']))
            continue
        logger.info("Creating md files for {}".format(connector['name']))
        base_url = connector['base_url']
        quoted_base_url = quote(base_url, safe="")
        file_keys = list_objects([quoted_base_url, ".html"])

        combined_file_content = ''
        for file_key in file_keys[:20]:
            logger.info("Generating .md file for {}".format(file_key))
            file_content = convert_html_to_md(read_object(file_key))
            upload_object(io.BytesIO(file_content.encode('utf-8')), file_key.rsplit('.html', 1)[0] + ".md")
            combined_file_content += file_content + "\n"

        upload_object(io.BytesIO(combined_file_content.encode('utf-8')), quoted_base_url + '-bulk' + '.md')

        unique_paragraphs = set(combined_file_content.split("\n\n"))
        upload_object(io.BytesIO("\n\n".join(unique_paragraphs).encode('utf-8')), quoted_base_url + '-bulk-concise' + '.md')

        extracted_links = []
        for paragraph in unique_paragraphs:
            links = detect_links(paragraph)
            extracted_links.extend(links)

            for link in links:
                context_start = max(0, paragraph.find(link) - 150)
                context_end = min(len(paragraph), paragraph.find(link) + len(link) + 150)
                logger.info(colored(paragraph[context_start:paragraph.find(link)], 'blue') +
                            colored(link, 'red') +
                            colored(paragraph[paragraph.find(link)+len(link):context_end], 'blue'))

        extracted_links = list(set(extracted_links))
        connector['endpoint_count'] = len(extracted_links)
        connector['endpoints'] = extracted_links

    if local:
        with open(filename, 'w') as f:
            json.dump(connectors, f, indent=4)
    else:
        updated_connectors = json.dumps(connectors, indent=4)
        file_obj = io.BytesIO(updated_connectors.encode('utf-8'))
        upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})

# Usage:
create_md_files('airbyte_connectors.json', local=True)