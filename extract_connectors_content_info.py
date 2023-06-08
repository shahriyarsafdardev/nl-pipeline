import io
import json
from urllib.parse import quote

from s3 import read_object
from logger import getLogger

logger = getLogger()


def load_json_from_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)


def load_json_from_s3(filename):
    file_content = read_object(filename)
    if file_content is None:
        return []
    return json.loads(file_content)


def save_output(output):
    try:
        with open('connectors_content_info.json', 'w') as f:
            json.dump(output, f, indent=4)
    except IOError as e:
        print(f"Unable to write to the output file: {e}")


def get_content_info(concise_bulk_file):
    paragraphs = len(concise_bulk_file.split('\n\n')) if concise_bulk_file else 0
    lines = len(concise_bulk_file.split('\n')) if concise_bulk_file else 0
    characters = len(concise_bulk_file)

    return {"paragraphs": paragraphs, "lines": lines, "characters": characters}


def extract_connector_content_info(filename, local = False):
    connectors = load_json_from_file(filename) if local else load_json_from_s3(filename)

    content_details = {}

    for connector in connectors:
        if connector.get('airbyte_status') != 'lowcode-connector':
            continue

        quoted_base_url = quote(connector['base_url'], safe="")
        concise_bulk_file = read_object(quoted_base_url + '-bulk-concise' + '.md')

        if concise_bulk_file is None:
            logger.info("Unable to find {} -bulk-concise.md".format(quoted_base_url))
            continue

        content_details[connector['name'].lower()] = get_content_info(concise_bulk_file)
        logger.info("Got content info for {}".format(connector['name']))

    return content_details


if __name__ == "__main__":
    content_info = extract_connector_content_info('airbyte_connectors.json', local=True)
    save_output(content_info)
