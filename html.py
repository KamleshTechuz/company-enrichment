import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict
import json

def get_all_urls(base_url: str) -> List[str]:
    """
    Fetches and returns all URLs found on the given website.
    
    :param base_url: The base URL of the website to scrape.
    :return: A list of URLs found on the website.
    """
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
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

def extract_data_from_url(url: str) -> Dict:
    """
    Extracts data from a single URL, including text content and specific HTML attributes.
    
    :param url: The URL to scrape.
    :return: A dictionary containing the extracted data.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text(separator=' ', strip=True)
        text_content = ' '.join(text_content.split())
        
        # Extract social links and other specific data
        social_links = {}
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'facebook.com' in href:
                social_links['facebook'] = href
            elif 'twitter.com' in href or 'x.com' in href:
                social_links['twitter'] = href
            elif 'linkedin.com' in href:
                social_links['linkedin'] = href
            elif 'pinterest.com' in href:
                social_links['pinterest'] = href
            elif 'instagram.com' in href:
                social_links['instagram'] = href
            elif 'youtube.com' in href:
                social_links['youtube'] = href
        
        # Extract other potential data from props or other attributes
        props_data = {}
        for tag in soup.find_all(attrs={"data-*": True}):
            props_data.update(tag.attrs)
        
        return {
            'url': url,
            'text_content': text_content,
            'social_links': social_links,
            'props_data': props_data
        }
    
    except Exception as e:
        print(f"Failed to fetch or parse the URL {url}: {str(e)}")
        return {
            'url': url,
            'text_content': '',
            'social_links': {},
            'props_data': {}
        }

def main():
    base_url = input("Enter the website URL to scrape: ")
    all_urls = get_all_urls(base_url)
    
    print(f"Found {len(all_urls)} URLs on {base_url}:")
    for url in all_urls:
        print(url)
    
    # all_data = []
    # for url in all_urls:
    #     data = extract_data_from_url(url)
    #     all_data.append(data)
    #     print(f"Extracted data from {url}:")
    #     print(json.dumps(data, indent=4))

if __name__ == "__main__":
    main()