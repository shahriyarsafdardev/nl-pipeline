import requests
from bs4 import BeautifulSoup
import io
import html2text
from s3 import upload_object
from urllib.parse import urljoin, urlparse, urlunparse, quote
from tqdm import tqdm
from logger import getLogger

logger = getLogger()


def download_html(page_url, verbose=False):
    """
    This function downloads the HTML content from a given URL.

    :param page_url: String containing the URL from which the HTML content is to be downloaded.
    :return: String containing the HTML content of the webpage. In case of an error, it returns None.
    """
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        if verbose:
            logger.info("Downloaded HTML from: %s", page_url)
        return response.text
    except Exception as e:
        if verbose:
            logger.error("Error downloading: %s", page_url, exc_info=True)
        return None

def extract_linked_urls(html, page_url, verbose=False):
    """
    This function extracts all the URLs present in the HTML content and makes them absolute links by
    joining with the base_url if they are relative links. It only returns unique URLs.

    :param html: String containing the HTML content from which URLs are to be extracted.
    :param base_url: String containing the base URL for resolving relative links.
    :return: A set of unique URLs extracted from the HTML content.
    """

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        if verbose:
            logger.error("Error parsing HTML: %s", str(e), exc_info=True)
        return set()

    # Find all the anchor tags in the HTML and get the href attribute
    linked_urls = [link.get("href") for link in soup.find_all("a")]

    # Make URLs absolute by joining with the base_url. If the URL is already absolute, it will be returned as is.
    linked_urls = [urljoin(page_url, url) for url in linked_urls if url]

    # Get unique URLs by converting the list to a set
    linked_urls = set(linked_urls)

    # Remove the query parameters and fragment identifiers from the URLs
    clean_urls = set()
    for url in linked_urls:
        parsed_url = urlparse(url)
        clean_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))
        clean_urls.add(clean_url)

    if verbose:
        logger.info(f"Found {len(clean_urls)} links in {page_url}")
        logger.info(clean_urls)

    return clean_urls

def scrape_domain(page_url, base_domain_url, verbose=False):
    """
    This function performs the web scraping operation starting from the page_url, 
    it then continues to scrape all the linked pages within the same domain (base_domain_url).

    :param page_url: String containing the start URL to begin the scraping process.
    :param base_domain_url: String containing the base URL for resolving relative links.
    :return: Set containing URLs that have been scraped.
    """
    to_scrape_urls = set([page_url])
    scraped_urls = set()

    with tqdm(total=len(to_scrape_urls), desc="URLs processed") as pbar:
        while to_scrape_urls:
            # Pick a URL from the to_scrape_urls set and remove it from the set
            url = to_scrape_urls.pop()
            scraped_urls.add(url)

            html = download_html(url, verbose=verbose)
            if not html:
                pbar.update(1)
                continue

            urls = extract_linked_urls(html, url, verbose=verbose)

            # Saving the HTML content to S3
            upload_object(io.BytesIO(html.encode()), quote(url, safe="")+".html", verbose=verbose)

            for url in urls:
                if base_domain_url not in url:  # Exclude URLs outside of the base domain
                    continue
                if url in scraped_urls:  # Exclude URLs already scraped
                    continue
                if url in to_scrape_urls:  # Exclude URLs already in the queue to be scraped
                    continue

                to_scrape_urls.add(url)
                pbar.total += 1

            pbar.update(1)

    return scraped_urls


def html_converter(text):
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    return converter.handle(text)