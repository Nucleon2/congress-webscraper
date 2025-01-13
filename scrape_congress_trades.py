import requests
from bs4 import BeautifulSoup
import csv
import sys
import time

BASE_URL = "https://www.capitoltrades.com"

def fetch_page(url):
    """
    Fetch a webpage and return a BeautifulSoup object, or None on error.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"[!] Error fetching {url}\n    {e}", file=sys.stderr)
        return None

def parse_trades_from_soup(soup):
    """
    Given a BeautifulSoup object for the /trades page, parse each row in the table.
    Returns a list of dictionaries with relevant fields.
    """
    trades_data = []
    
    # The main table for the trades:
    table = soup.select_one("table.w-full.caption-bottom.text-size-3.text-txt")
    if not table:
        print("[!] Could not find the main trades table.")
        return trades_data
    
    rows = table.select("tbody tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 9:
            continue  # Skip if columns aren't as expected
        
        # Map the columns to fields
        politician_name = cols[0].get_text(strip=True)
        traded_issuer   = cols[1].get_text(strip=True)
        published_date  = cols[2].get_text(strip=True)
        traded_date     = cols[3].get_text(strip=True)
        days_diff       = cols[4].get_text(strip=True)
        owner_str       = cols[5].get_text(strip=True)
        tx_type         = cols[6].get_text(strip=True).lower()
        size_str        = cols[7].get_text(strip=True)
        price_str       = cols[8].get_text(strip=True)
        
        trades_data.append({
            "Politician": politician_name,
            "Issuer": traded_issuer,
            "PublishedDate": published_date,
            "TradedDate": traded_date,
            "DaysAfter": days_diff,
            "Owner": owner_str,
            "Type": tx_type,
            "SizeRange": size_str,
            "Price": price_str,
        })
    return trades_data

def find_next_page_url(soup):
    """
    Looks for the link: <a aria-label="Go to next page" href="..."> 
    Returns full absolute URL if found, else None.
    """
    next_link = soup.select_one('a[aria-label="Go to next page"]')
    if next_link and next_link.get("href"):
        relative = next_link["href"]
        return BASE_URL + relative
    return None

def scrape_capitol_trades(start_url, output_csv="capitol_trades.csv"):
    """
    Iterates through all pages (if paginated) and scrapes trades into CSV.
    """
    visited = set()
    current_url = start_url
    
    fieldnames = [
        "Politician", "Issuer", "PublishedDate", "TradedDate",
        "DaysAfter", "Owner", "Type", "SizeRange", "Price"
    ]
    
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        while current_url and current_url not in visited:
            visited.add(current_url)
            print(f"[*] Scraping: {current_url}")
            
            soup = fetch_page(current_url)
            if not soup:
                print(f"[!] Skipping page due to fetch error: {current_url}")
                break
            
            trades = parse_trades_from_soup(soup)
            for t in trades:
                writer.writerow(t)
            
            # Move on to next page if available
            next_page = find_next_page_url(soup)
            current_url = next_page
            time.sleep(1)  # polite delay

    print(f"[+] Finished scraping. CSV saved to {output_csv}")

def main():
    # Start from page=1
    start_url = "https://www.capitoltrades.com/trades?page=1"
    scrape_capitol_trades(start_url)

if __name__ == "__main__":
    main()
