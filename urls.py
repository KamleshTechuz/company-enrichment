import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List  # Import List from typing module

def get_all_urls(base_url: str) -> List[str]:
    """
    Fetches and returns all URLs found on the given website.
    
    :param base_url: The base URL of the website to scrape.
    :return: A list of URLs found on the website.
    """
    try:
        # Fetch the webpage content
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all URLs
        urls = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                urls.add(full_url)
        
        return list(urls)
    
    except Exception as e:
        print(f"Failed to fetch or parse the website: {str(e)}")
        return []

if __name__ == "__main__":
    # Example usage
    base_url = input("Enter the website URL to scrape: ")
    urls = get_all_urls(base_url)
    print(f"Found {len(urls)} URLs on {base_url}:")
    for url in urls:
        print(url)