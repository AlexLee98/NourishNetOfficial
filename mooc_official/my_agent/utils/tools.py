
from langchain_core.tools import tool

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Optional, List

# Get current page
def scrape_page(page_number: int) -> Optional[BeautifulSoup]:

    url = f'https://www.costco.com/grocery-household.html?currentPage={page_number}&dept=All&pageSize=24&sortBy=score+desc&keyword=OFF'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive'
    }

    r = requests.get(url, headers = headers)

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    return soup


# Get grocery deals
@tool
def extract_costco_deals() -> str:
    """Call to look for ingridents to buy """
    groceries_list = []
    page_number = 1

    while True:
        soup = scrape_page(page_number)
        if soup is None:
            break

        # Get all groceries
        groceries = soup.find_all('div', class_='caption link-behavior')

        if not groceries:
            break

        # Extract and store product details
        for grocery in groceries:

            # Get grocery name
            title_tag = grocery.find('span', class_ = 'description')
            if title_tag:
                title = title_tag.get_text(strip = True)

                # Get price
                price_tag = grocery.find('div', class_ = 'price')
                if price_tag:
                    price = price_tag.get_text(strip = True)

                    # Get discount
                    promo_tag = grocery.find('p', class_ = 'promo')
                    promo = promo_tag.get_text(strip = True) if promo_tag else 0
                    discount_match = re.search(r'\$(\d+(\.\d+)?)', promo)
                    discount_amount = float(discount_match.group(1)) if discount_match else None

                    # Insert into json
                    discounted_price = float(price.split('$')[1])
                    original_price = round(discounted_price + discount_amount, 2)
                    grocery_json = {
                        'Name': title,
                        'Discounted Price': float(price.split('$')[1]), 
                        'Original Price' : original_price,
                        'Discount': discount_amount 
                    }

                    groceries_list.append(grocery_json)

        page_number += 1


    return json.dumps(groceries_list)


#Simulate a tool which can query a database for the current pantry inventory
def return_ingredients_list() -> dict:
    x = {
    "egg": 10,
    "salt": "1 bottle",
    "sugar" : "1 box",
    "water" : "100 gallons",
    "pepper" : 10,
    "green onions": 3,
    "onions": 10,
    "garlic gloves" : 10,
    "soy sauce" : "1 bottle",
    "chili paste" : "1 bottle",
    "cooking oil" : "1 bottle",
    "olive oil" : "1 bottle",
    "pasta" : 10,
    "parsley" : 5,
    "butter" : "1 box",
    "ginger" : 5
    }

    # convert into JSON:
    y = json.dumps(x)
    return y