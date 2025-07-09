import os, re, requests, json, streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, openai_api_key=os.getenv("OPENAI_API_KEY"))

def extract_company_info(base_url):
    headers = {'User-Agent': 'Mozilla'}
    paths = ["", "about", "contact", "team", "company", "legal"]
    text, links, phone, email = '', {}, '', ''
    for path in paths:
        try:
            u = urljoin(base_url, f"/{path}")
            r = requests.get(u, headers=headers, timeout=5)
            if r.status_code != 200: continue
            s = BeautifulSoup(r.text, 'html.parser')
            text += re.sub(r'\s+', ' ', s.get_text(' ', strip=True)) + ' '
            for a in s.find_all('a', href=True):
                for k in ['linkedin','facebook','twitter','pinterest']:
                    if k in a['href'] and k not in links:
                        links[k] = urljoin(base_url, a['href'])
        except: continue
    emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
    phones = re.findall(r'\+?\d[\d\s()-]{7,}\d', text)
    email = emails[0] if emails else ''
    phone = phones[0] if phones else ''
    prompt = f"""
From the following text and metadata, extract a JSON object with the following fields:
Text: {text[:12000]}
Social: {links}
Email: {email}
Phone: {phone}
Format:
{{
  "legal_name": "", "description": "", "industry": "", "employees": "", "annual_revenue": "",
  "linkedin": "", "facebook": "", "twitter": "", "pinterest": "",
  "address": {{"street": "", "city": "", "state": "", "zip": "", "country": ""}},
  "sic_code": "", "phone": "", "email": ""
}}"""
    j = llm.predict(prompt).strip()
    return json.loads(j[j.find('{'):j.rfind('}')+1])

st.set_page_config(page_title="Company Info Extractor", layout="centered")
st.title("🔍 Company Info Extractor")
url = st.text_input("Enter company website URL", "https://techuz.com")
if st.button("Extract") and url:
    with st.spinner("Extracting..."):
        try:
            data = extract_company_info(url)
            st.success("Extraction complete!")
            st.json(data)
        except Exception as e:
            st.error(f"Error: {e}")
