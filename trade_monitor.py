import requests
from bs4 import BeautifulSoup
import csv
import time
import sys

BASE_URL = "https://www.capitoltrades.com"
CSV_FILE = "capitol_trades.csv"

def load_known_ids(csv_path):
    """
    Read existing CSV, build a set of unique trade IDs.
    """
    known = set()
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # For example: Use a combination of columns to identify uniqueness
                # Politician|TradedDate|Issuer|Type
                unique_id = (
                    row["Politician"] + 
                    row["TradedDate"] + 
                    row["Issuer"] + 
                    row["Type"]
                )
                known.add(unique_id)
    except FileNotFoundError:
        print(f"[!] {csv_path} not found, starting fresh.")
    return known

def fetch_page(url):
    """
    Fetch a webpage and return a BeautifulSoup object, or None on error.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
    table = soup.select_one("table.w-full.caption-bottom.text-size-3.text-txt")
    if not table:
        print("[!] Could not find the main trades table.")
        return trades_data
    
    rows = table.select("tbody tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 9:
            continue
        
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
        return BASE_URL + next_link["href"]
    return None

def check_for_new_trades(known_ids, csv_path):
    """
    Check the website for new trades, compare to known_ids set,
    append new ones to CSV. Returns count of new trades found.
    """
    new_count = 0
    current_url = "https://www.capitoltrades.com/trades?page=1"
    visited = set()

    # We'll limit how many pages we fetch, or continue until no next-page link.
    # Usually, new trades appear on page=1. We might parse 2–3 pages just in case.
    # Adjust as needed if you see new trades appear deeper in pagination.
    while current_url and current_url not in visited:
        visited.add(current_url)
        print(f"[*] Checking page: {current_url}")
        
        soup = fetch_page(current_url)
        if not soup:
            break
        
        # Grab trades from that page
        trades = parse_trades_from_soup(soup)
        if not trades:
            # possibly no table or empty
            break

        # Open CSV in append mode
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Politician","Issuer","PublishedDate","TradedDate",
                    "DaysAfter","Owner","Type","SizeRange","Price"
                ]
            )
            
            # if the file was empty, we need a header, but let's assume we
            # already had a header from the previous run. If brand-new, you can check:
            #   import os
            #   if os.path.getsize(csv_path) == 0:
            #       writer.writeheader()
            
            for t in trades:
                # Make the same unique key as we used in load_known_ids
                unique_id = (
                    t["Politician"] + 
                    t["TradedDate"] + 
                    t["Issuer"] + 
                    t["Type"]
                )
                
                if unique_id not in known_ids:
                    # This is a new trade
                    writer.writerow(t)
                    known_ids.add(unique_id)
                    new_count += 1

        next_url = find_next_page_url(soup)
        # Let's only fetch at most 3 pages to find recent trades
        # (You can increase or remove if you want to go deeper)
        if next_url and len(visited) < 3:
            current_url = next_url
        else:
            break

    return new_count

def main_loop():
    # Load initial known IDs from the existing CSV
    known_ids = load_known_ids(CSV_FILE)

    while True:
        print("[+] Checking for new trades…")
        new_trades_found = check_for_new_trades(known_ids, CSV_FILE)
        
        if new_trades_found > 0:
            print(f"[+] Found {new_trades_found} new trades!")
        else:
            print("[+] No new trades at this time.")
        
        # Wait an hour (3600 seconds) before checking again
        # Adjust to your liking (minutes, days, etc.)
        time.sleep(3600)

if __name__ == "__main__":
    main_loop()
