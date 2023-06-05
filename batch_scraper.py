import json
from scraper import scrape_domain

def run_scrapers(filename):
    """
    This function reads the JSON file with scraper configurations and runs the scrape function for each configuration.

    :param filename: String containing the path to the JSON file.
    :return: None
    """
    with open(filename, 'r') as f:
        connectors = json.load(f)

    for connector in connectors:
        name = connector['name']
        base_url = connector['base_url']
        start_url = connector['start_url']
        
        print(f"Running scraper for: {name}")
        scrape_domain(start_url, base_url)

# Usage:
run_scrapers('airbyte_connectors.json')
