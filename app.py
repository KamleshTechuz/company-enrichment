import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI
from urllib.parse import urlparse
import os

from dotenv import load_dotenv
load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_domain(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def crawl_links(base_url, limit=5):
    visited, to_visit = set(), [base_url]
    texts = []

    while to_visit and len(visited) < limit:
        url = to_visit.pop(0)
        if url in visited: continue
        visited.add(url)

        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            [s.decompose() for s in soup(["script", "style", "noscript"])]
            texts.append(soup.get_text(separator=" ", strip=True))
            
            for tag in soup.find_all("a", href=True):
                link = urljoin(base_url, tag["href"])
                if link.startswith(base_url) and link not in visited:
                    to_visit.append(link)
        except:
            continue

    return " ".join(texts)[:24000]  # Trim to fit LLM limit

def get_company_info(text, url):
    prompt = f"""Extract the following information from this company:
URL: {url}
Content: {text}
Return JSON with keys: legal_name, description, industry, employees, annual_revenue, linkedin, facebook, twitter, pinterest, address (street, city, state, zip, country), sic_code.
Respond only in compact JSON."""
    
    res = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return res.choices[0].message.content

st.title("🔎 Company Enrichment from Website")
url = st.text_input("Enter Company Website URL")

if st.button("Enrich") and url:
    with st.spinner("Crawling and extracting..."):
        base = get_domain(url)
        text = crawl_links(base)
        if not text:
            st.error("Failed to extract content.")
        else:
            info = get_company_info(text, url)
            st.code(info, language="json")
