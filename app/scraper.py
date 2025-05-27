import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

BASE_URL = "https://www.madewithnestle.ca/"
DATA_DIR = "data/scraped"

def scrape_nestle_site() -> List[Dict]:
    """Scrape product data from the Made With Nestlé website"""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    try:
        # Fetch main page
        main_page = requests.get(BASE_URL, timeout=10)
        main_page.raise_for_status()
        soup = BeautifulSoup(main_page.text, "html.parser")
        
        # Extract product links
        product_links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/products/" in href:
                product_links.add(urljoin(BASE_URL, href))
        
        # Scrape individual product pages
        products = []
        for url in product_links:
            try:
                product = scrape_product_page(url)
                if product:
                    products.append(product)
                    save_product_data(product)
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
        
        # Save combined data
        with open(f"{DATA_DIR}/all_products.json", "w") as f:
            json.dump(products, f)
            
        return products
        
    except Exception as e:
        print(f"Failed to scrape main page: {str(e)}")
        return []

def scrape_product_page(url: str) -> Dict:
    """Scrape data from a single product page"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        product = {
            "url": url,
            "title": extract_text(soup.find("h1")),
            "description": extract_text(soup.find("div", class_="product-description")),
            "nutrition": extract_nutrition(soup),
            "categories": extract_categories(soup),
            "scraped_at": datetime.now().isoformat()
        }
        
        return product
    except Exception as e:
        print(f"Error scraping product page {url}: {str(e)}")
        return None

def extract_text(element) -> str:
    """Extract cleaned text from HTML element"""
    return element.get_text(strip=True) if element else ""

def extract_nutrition(soup: BeautifulSoup) -> Dict:
    """Extract nutrition facts from table"""
    nutrition = {}
    table = soup.find("table", class_="nutrition-table")
    if table:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                nutrition[key] = value
    return nutrition

def extract_categories(soup: BeautifulSoup) -> List[str]:
    """Extract categories from breadcrumbs"""
    categories = []
    breadcrumbs = soup.find("nav", class_="breadcrumb")
    if breadcrumbs:
        categories = [
            a.get_text(strip=True) 
            for a in breadcrumbs.find_all("a")
            if a.get_text(strip=True)
        ]
    return categories

def save_product_data(product: Dict):
    """Save individual product data to JSON file"""
    filename = f"{hash(product['url'])}.json"
    with open(f"{DATA_DIR}/{filename}", "w") as f:
        json.dump(product, f)

def hash(url: str) -> str:
    """Generate consistent hash for filenames"""
    return str(abs(hash(url)))