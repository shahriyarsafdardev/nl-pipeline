import requests
from bs4 import BeautifulSoup
import io
from s3 import upload_object
from logger import getLogger

logger = getLogger()


def download_html(page_url):
    """
    This function downloads the HTML content from a given URL.

    :param page_url: String containing the URL from which the HTML content is to be downloaded.
    :return: String containing the HTML content of the webpage. In case of an error, it returns None.
    """
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error("Error downloading: %s", page_url, exc_info=True)
        return None

def extract_linked_urls(html):
    """
    This function extracts all the URLs present in the HTML content.

    :param html: String containing the HTML content from which URLs are to be extracted.
    :return: A list of URLs extracted from the HTML content.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = [link.get("href") for link in soup.find_all("a")]
    urls = [url for url in urls if url]
    return urls

def scrape_domain(page_url, base_domain_url, scraped_urls=set()):
    """
    This function performs the web scraping operation starting from the page_url, 
    it then continues to scrape all the linked pages within the same domain (base_domain_url).

    :param page_url: String containing the start URL to begin the scraping process.
    :param base_domain_url: String containing the base URL for resolving relative links and filtering out external links.
    :param scraped_urls: Set containing URLs that have already been scraped. Defaults to an empty set.
    :return: None
    """

    scraped_urls.add(page_url)

    html = download_html(page_url)
    if not html:
        return

    urls = extract_linked_urls(html)

    # Filtering out the URLs not in the same domain and those already scraped
    filtered_urls = []
    for url in urls:
        if base_domain_url in url and url not in scraped_urls:
            filtered_urls.append(url)

    # Saving the HTML content to S3
    upload_object(io.BytesIO(html.encode()), page_url)

    for url in filtered_urls:
        scrape_domain(url, base_domain_url, scraped_urls)
