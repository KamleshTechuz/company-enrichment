import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os

from dotenv import load_dotenv
load_dotenv()


openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def scrape_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        [s.decompose() for s in soup(["script", "style", "noscript"])]
        return soup.get_text(separator=" ", strip=True)[:12000]
    except:
        return ""

def get_company_info(text, url):
    prompt = f"""Extract the following information from this website:
URL: {url}
Content: {text}
Return in JSON format with keys: legal_name, description, industry, employees, annual_revenue, linkedin, facebook, twitter, pinterest, address (street, city, state, zip, country), sic_code.
Respond only with JSON."""
    
    res = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return res.choices[0].message.content

st.title("Company Enrichment from Website")
url = st.text_input("Enter Company Website URL")

if st.button("Enrich") and url:
    with st.spinner("Extracting information..."):
        text = scrape_text(url)
        if not text:
            st.error("Failed to extract content from the website.")
        else:
            info = get_company_info(text, url)
            st.code(info, language="json")
