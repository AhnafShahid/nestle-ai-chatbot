import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
from typing import Dict, List
import hashlib
from datetime import datetime

BASE_URL = "https://www.madewithnestle.ca/"
DATA_DIR = "data/scraped"
os.makedirs(DATA_DIR, exist_ok=True)

def get_page_content(url: str) -> str:
    """Fetch page content with error handling"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; NestleAIBot/1.0; +https://www.madewithnestle.ca/bot)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return ""

def extract_product_info(soup: BeautifulSoup, url: str) -> Dict:
    """Extract product information from a product page"""
    product = {
        "url": url,
        "title": soup.find("h1").get_text(strip=True) if soup.find("h1") else "",
        "description": "",
        "nutrition": {},
        "categories": [],
        "scraped_at": datetime.now().isoformat()
    }
    
    # Extract description
    desc_div = soup.find("div", class_="product-description")
    if desc_div:
        product["description"] = desc_div.get_text(strip=True)
    
    # Extract nutrition facts
    nutrition_table = soup.find("table", class_="nutrition-table")
    if nutrition_table:
        for row in nutrition_table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                product["nutrition"][key] = value
    
    # Extract categories from breadcrumbs
    breadcrumbs = soup.find("nav", class_="breadcrumb")
    if breadcrumbs:
        product["categories"] = [
            a.get_text(strip=True) 
            for a in breadcrumbs.find_all("a") 
            if a.get_text(strip=True)
        ]
    
    return product

def scrape_nestle_site() -> List[Dict]:
    """Main scraping function that crawls the site"""
    print("Starting to scrape Nestlé website...")
    visited_urls = set()
    products = []
    
    # Start with the main page
    main_page = get_page_content(BASE_URL)
    if not main_page:
        return []
    
    soup = BeautifulSoup(main_page, "html.parser")
    
    # Find all product links
    product_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(BASE_URL, href)
        if "/products/" in full_url and full_url not in product_links:
            product_links.add(full_url)
    
    # Process each product page
    for i, product_url in enumerate(product_links):
        print(f"Scraping product {i+1}/{len(product_links)}: {product_url}")
        if product_url in visited_urls:
            continue
            
        visited_urls.add(product_url)
        page_content = get_page_content(product_url)
        if not page_content:
            continue
            
        product_soup = BeautifulSoup(page_content, "html.parser")
        product_info = extract_product_info(product_soup, product_url)
        products.append(product_info)
        
        # Save each product individually
        product_hash = hashlib.md5(product_url.encode()).hexdigest()
        with open(f"{DATA_DIR}/{product_hash}.json", "w") as f:
            json.dump(product_info, f)
    
    # Save combined data
    with open(f"{DATA_DIR}/all_products.json", "w") as f:
        json.dump(products, f)
    
    print(f"Scraping complete. Found {len(products)} products.")
    return products