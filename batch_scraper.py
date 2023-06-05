import json
import io
from scraper import scrape_domain
from logger import getLogger
from s3 import read_object, upload_object

logger = getLogger()


def run_scrapers(filename):
    """
    This function reads the JSON file with scraper configurations and runs the scrape function for each configuration.

    :param filename: String containing the path to the JSON file.
    :return: None
    """
    # Reading file from S3
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

        # Uploading the updated connector data list to S3
        connectors = json.dumps(connectors, indent=4)
        file_obj = io.BytesIO(connectors.encode('utf-8'))
        upload_object(file_obj, filename, extraArgs={'CacheControl': 'no-store'})

# Usage:
run_scrapers('airbyte_connectors.json')
