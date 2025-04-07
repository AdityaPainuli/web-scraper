import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
import os


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")



supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_nested_in_tag(tag, parent_tags):
    current = tag.parent
    while current:
        if current.name in parent_tags:
            return True
        current = current.parent
    return False

def scrape_filter_and_store_text(url):
    """
    Scrape, filter text, and save into Supabase table.
    """
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

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

    full_text = '\n\n'.join(extracted_text)

    data = {
        "url": url,
        "content": full_text
    }

    response = supabase.table("scraped_content").insert(data).execute()

    print("Data saved to Supabase:", response.data)

if __name__ == "__main__":
    url = "https://www.givecentral.org/online-fundraiser-non-profit-organizations"  
    scrape_filter_and_store_text(url)
