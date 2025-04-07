from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
import os

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- FastAPI App ----
app = FastAPI()

# ---- Request Model ----
class CrawlRequest(BaseModel):
    url: HttpUrl

# ---- Helper functions ----
def is_nested_in_tag(tag, parent_tags):
    current = tag.parent
    while current:
        if current.name in parent_tags:
            return True
        current = current.parent
    return False

def scrape_filtered_text(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove navbars and footers
    for unwanted in soup.find_all(['nav', 'footer']):
        unwanted.decompose()

    for class_name in ['navbar', 'header', 'footer', 'site-header']:
        for tag in soup.find_all(class_=class_name):
            tag.decompose()

    extracted_text = []
    for tag_name in ['div', 'section']:
        for element in soup.find_all(tag_name):
            if not is_nested_in_tag(element, ['div', 'section']):
                text = element.get_text(separator=' ', strip=True)
                if text:
                    extracted_text.append(text)

    return '\n\n'.join(extracted_text)

# ---- API Route ----
@app.post("/crawl")
def crawl_url(request: CrawlRequest):
    try:
        # Scrape & clean content
        content = scrape_filtered_text(request.url)

        # Save to Supabase
        data = {
            "url": str(request.url),
            "content": content
        }
        result = supabase.table("scraped_content").insert(data).execute()

        return {
            "message": "Crawling and storage successful",
            "data": result.data
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
