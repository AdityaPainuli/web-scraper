from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
import logging

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CrawlRequest(BaseModel):
    url: HttpUrl


def scrape_filtered_text(url: str) -> dict:
    logger.info(f"Scraping content from {url}")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')


    title_tag = soup.find("h1", class_="entry-title")
    title = title_tag.get_text(strip=True) if title_tag else "No Title Found"


    entry_div = soup.find("div", class_="entry")
    body = entry_div.get_text(separator="\n", strip=True) if entry_div else "No Body Content Found"

    return {
        "title": title,
        "body": body
    }


def extract_urls_from_sitemap(sitemap_url: str, limit: int = 10) -> list:
    logger.info(f"Fetching sitemap: {sitemap_url}")
    response = requests.get(sitemap_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "xml")

    url_tags = soup.find_all("url")
    urls = []

    for tag in url_tags:
        loc_tag = tag.find("loc")
        if loc_tag and loc_tag.text:
            url = loc_tag.text.strip()
            urls.append(url)
            logger.info(f"Found URL: {url}")
        if len(urls) >= limit:
            break

    logger.info(f"Total URLs extracted: {len(urls)}")
    return urls


@app.post("/crawl")
def crawl_url(request: CrawlRequest):
    try:
        content = scrape_filtered_text(request.url)

        # Save to Supabase
        data = {
            "url": str(request.url),
            "title": content["title"],
            "content": content["body"]
        }
        result = supabase.table("scraped_content").insert(data).execute()

        return {
            "message": "Crawling and storage successful",
            "data": result.data
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise HTTPException(status_code=400, detail=f"Request failed: {e}")

    except Exception as e:
        logger.exception("Internal error")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    
    
@app.get("/crawl-sitemap")
def crawl_from_sitemap(sitemap_url: str):
    try:
        urls = extract_urls_from_sitemap(sitemap_url, limit=10)
        logger.info(f"Starting to scrape {len(urls)} URLs...")

        scraped_data = []

        for idx, url in enumerate(urls, start=1):
            logger.info(f"[{idx}/10] Scraping {url}")
            try:
                content = scrape_filtered_text(url)

                scraped_data.append({
                    "url": url,
                    "title": content["title"],
                    "body": content["body"]
                })
                logger.info(f"[{idx}/10] Scraped successfully")

            except Exception as e:
                logger.error(f"[{idx}/10] Error scraping {url}: {e}")
                scraped_data.append({
                    "url": url,
                    "error": str(e)
                })

        return {
            "message": f"Scraped {len(scraped_data)} blog posts from sitemap.",
            "data": scraped_data
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Sitemap request failed: {e}")
        raise HTTPException(status_code=400, detail=f"Sitemap request failed: {e}")

    except Exception as e:
        logger.exception("Internal error")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
