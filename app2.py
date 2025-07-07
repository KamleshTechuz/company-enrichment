import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

load_dotenv()

@dataclass
class CompanyInfo:
    legal_name: str = ""
    description: str = ""
    industry: str = ""
    employees: str = ""
    annual_revenue: str = ""
    linkedin: str = ""
    facebook: str = ""
    twitter: str = ""
    pinterest: str = ""
    address: Dict = None
    sic_code: str = ""
    phone: str = ""
    email: str = ""

class EnhancedWebScraper:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Using mini for cost efficiency
            temperature=0.1,
            openai_api_key=openai_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len
        )
        
    def get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def extract_structured_data(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Extract structured data from HTML elements"""
        structured_data = {
            'social_links': {},
            'contact_info': {},
            'metadata': {}
        }
        
        # Extract social media links
        social_patterns = {
            'linkedin': r'linkedin\.com',
            'facebook': r'facebook\.com',
            'twitter': r'twitter\.com|x\.com',
            'pinterest': r'pinterest\.com',
            'instagram': r'instagram\.com',
            'youtube': r'youtube\.com'
        }
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            full_url = urljoin(base_url, href)
            
            for platform, pattern in social_patterns.items():
                if re.search(pattern, full_url, re.IGNORECASE):
                    structured_data['social_links'][platform] = full_url
                    break
        
        # Extract contact information
        text_content = soup.get_text()
        
        # Phone numbers
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, text_content)
        if phones:
            structured_data['contact_info']['phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text_content)
        if emails:
            structured_data['contact_info']['email'] = emails[0]
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '')
            if name in ['description', 'keywords'] and content:
                structured_data['metadata'][name] = content
        
        return structured_data
    
    def get_priority_pages(self, base_url: str) -> List[str]:
        """Get priority pages that are most likely to contain company info"""
        priority_paths = [
            '', '/', '/about', '/about-us', '/company', '/contact', 
            '/team', '/leadership', '/careers', '/services', '/products'
        ]
        
        pages = []
        for path in priority_paths:
            if path == '' or path == '/':
                pages.append(base_url)
            else:
                pages.append(urljoin(base_url, path))
        
        return pages
    
    def scrape_page(self, url: str) -> Optional[Dict]:
        """Scrape a single page and return structured data"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'noscript', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Extract structured data
            structured_data = self.extract_structured_data(soup, url)
            
            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {
                'url': url,
                'text': text,
                'structured_data': structured_data
            }
            
        except Exception as e:
            st.warning(f"Failed to scrape {url}: {str(e)}")
            return None
    
    def crawl_company_site(self, base_url: str, max_pages: int = 5) -> List[Dict]:
        """Crawl company website focusing on priority pages"""
        base_domain = self.get_domain(base_url)
        priority_pages = self.get_priority_pages(base_domain)
        
        scraped_data = []
        visited = set()
        
        # First, scrape priority pages
        for page_url in priority_pages[:max_pages]:
            if page_url not in visited:
                page_data = self.scrape_page(page_url)
                if page_data and page_data['text']:
                    scraped_data.append(page_data)
                    visited.add(page_url)
        
        return scraped_data
    
    def create_company_summary(self, scraped_data: List[Dict]) -> str:
        """Create a concise summary of company information using LangChain"""
        
        # Combine all structured data
        all_social_links = {}
        all_contact_info = {}
        all_metadata = {}
        
        for data in scraped_data:
            structured = data.get('structured_data', {})
            all_social_links.update(structured.get('social_links', {}))
            all_contact_info.update(structured.get('contact_info', {}))
            all_metadata.update(structured.get('metadata', {}))
        
        # Prepare documents for summarization
        documents = []
        for data in scraped_data:
            # Prioritize about and contact pages
            priority_score = 1.0
            if any(keyword in data['url'].lower() for keyword in ['about', 'contact', 'company']):
                priority_score = 2.0
            
            doc = Document(
                page_content=data['text'][:1500],  # Limit individual page content
                metadata={
                    'url': data['url'],
                    'priority': priority_score
                }
            )
            documents.append(doc)
        
        # Create summary prompt
        summary_prompt = PromptTemplate(
            template="""
            Analyze the following company website content and extract key information:
            
            {text}
            
            Focus on identifying:
            1. Company name and legal entity name
            2. Business description and industry
            3. Company size indicators (employees, revenue mentions)
            4. Key services or products
            5. Location/address information
            
            Provide a concise summary in 3-4 sentences focusing on the most important company details.
            """,
            input_variables=["text"]
        )
        
        # Use map-reduce for large content
        if len(documents) > 1:
            summarize_chain = load_summarize_chain(
                self.llm,
                chain_type="map_reduce",
                map_prompt=summary_prompt,
                combine_prompt=PromptTemplate(
                    template="Combine the following summaries into a comprehensive company profile:\n\n{text}",
                    input_variables=["text"]
                )
            )
            summary = summarize_chain.run(documents)
        else:
            summary = self.llm.predict(summary_prompt.format(text=documents[0].page_content))
        
        return {
            'summary': summary,
            'social_links': all_social_links,
            'contact_info': all_contact_info,
            'metadata': all_metadata
        }
    
    def extract_company_info(self, company_data: Dict, base_url: str) -> str:
        """Extract structured company information using the summary"""
        
        extraction_prompt = f"""
        Based on the following company information, extract structured data:
        
        Website: {base_url}
        Summary: {company_data['summary']}
        Social Links: {company_data['social_links']}
        Contact Info: {company_data['contact_info']}
        Metadata: {company_data['metadata']}
        
        Extract and return ONLY a JSON object with these exact keys:
        {{
            "legal_name": "Company legal name",
            "description": "Brief business description",
            "industry": "Industry sector",
            "employees": "Employee count or range",
            "annual_revenue": "Revenue information if available",
            "linkedin": "LinkedIn URL",
            "facebook": "Facebook URL", 
            "twitter": "Twitter/X URL",
            "pinterest": "Pinterest URL",
            "address": {{
                "street": "Street address",
                "city": "City",
                "state": "State",
                "zip": "ZIP code",
                "country": "Country"
            }},
            "sic_code": "SIC code if determinable",
            "phone": "Phone number",
            "email": "Email address"
        }}
        
        Use "Not found" for missing information. Return only the JSON object.
        """
        
        try:
            response = self.llm.predict(extraction_prompt)
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            elif response.startswith('```'):
                response = response[3:-3]
            
            return response
        except Exception as e:
            st.error(f"Error extracting company info: {str(e)}")
            return "{}"

def main():
    st.title("🔎 Enhanced Company Enrichment Tool")
    st.markdown("*Powered by LangChain and intelligent web scraping*")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    max_pages = st.sidebar.slider("Max pages to crawl", 1, 10, 5)
    
    # Main input
    url = st.text_input("Enter Company Website URL", placeholder="https://example.com")
    
    if st.button("🚀 Enrich Company Data") and url:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Please set your OPENAI_API_KEY in the .env file")
            return
        
        with st.spinner("🔍 Crawling website and extracting data..."):
            try:
                scraper = EnhancedWebScraper(os.getenv("OPENAI_API_KEY"))
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Crawl website
                status_text.text("Crawling priority pages...")
                progress_bar.progress(25)
                scraped_data = scraper.crawl_company_site(url, max_pages)
                
                if not scraped_data:
                    st.error("Failed to extract content from the website")
                    return
                
                # Step 2: Create summary
                status_text.text("Creating company summary...")
                progress_bar.progress(50)
                company_summary = scraper.create_company_summary(scraped_data)
                
                # Step 3: Extract structured info
                status_text.text("Extracting structured information...")
                progress_bar.progress(75)
                company_info = scraper.extract_company_info(company_summary, url)
                
                progress_bar.progress(100)
                status_text.text("✅ Enrichment complete!")
                
                # Display results
                st.success("Company enrichment completed successfully!")
                
                # Show the extracted JSON
                st.subheader("📋 Extracted Company Information")
                st.code(company_info, language="json")
                
                # Show additional insights
                with st.expander("🔍 Additional Insights"):
                    st.write("**Company Summary:**")
                    st.write(company_summary['summary'])
                    
                    if company_summary['social_links']:
                        st.write("**Social Media Presence:**")
                        for platform, link in company_summary['social_links'].items():
                            st.write(f"- {platform.title()}: {link}")
                    
                    st.write(f"**Pages Analyzed:** {len(scraped_data)}")
                    for i, data in enumerate(scraped_data, 1):
                        st.write(f"{i}. {data['url']}")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error("Please check your API key and try again.")

if __name__ == "__main__":
    main()