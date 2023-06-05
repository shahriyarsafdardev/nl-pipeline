import json
import io
from scraper import scrape_domain
from logger import getLogger
from s3 import read_object, upload_object

logger = getLogger()

def merge_arrays(arr1, arr2):
    key_dict = {(obj['name'], obj['base_url']): obj for obj in arr2}
    
    for obj in arr1:
        name = obj['name']
        base_url = obj['base_url']
        key = (name, base_url)
        if key in key_dict:
            key_dict[key] = obj
        else:
            key_dict[key] = obj
    
    merged_array = list(key_dict.values())
    return merged_array


def run_scrapers(filename):
    """
    This function reads the JSON file with scraper configurations and runs the scrape function for each configuration.

    :param filename: String containing the path to the JSON file.
    :return: None
    """
    file_content = read_object(filename)
    connectors = json.loads(file_content)

    for connector in connectors:
        # Check if this connector has already been scraped
        if "scraped_page_count" in connector:
            logger.info(f'Skipping {connector["name"]}, already scraped {connector["scraped_page_count"]} pages.')
            continue
        
        name = connector['name']
        base_url = connector['base_url']
        start_url = connector['start_url']
        
        scraped_urls = scrape_domain(start_url, base_url, verbose=False)

        # Log the number of URLs scraped for each connector
        logger.info(f'Scraper for {name} completed. Total URLs scraped: {len(scraped_urls)}')

        # Update the connector dictionary with the count of scraped pages
        connector['scraped_page_count'] = len(scraped_urls)

        current_connectors_file = read_object(filename)
        current_connectors = json.loads(current_connectors_file)

        merged_arrays = merge_arrays(connectors, current_connectors)
        merged_arrays = json.dumps(merged_arrays, indent=4)
        file_obj = io.BytesIO(merged_arrays.encode('utf-8'))
        upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})

# Usage:
run_scrapers('airbyte_connectors.json')
