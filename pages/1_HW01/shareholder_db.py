import requests
import time
import os
import json
from datetime import datetime
from pathlib import Path

# Complete list of SET50 tickers
SET50_SYMBOLS = [
    "ADVANC", "AOT", "AWC", "BANPU", "BBL", "BDMS", "BEM", "BH", "BJC", "BTS",
    "CBG", "CCET", "CENTEL", "COM7", "CPALL", "CPF", "CPN", "CRC", "DELTA", "EGCO",
    "GPSC", "GULF", "HMPRO", "IVL", "KBANK", "KKP", "KTB", "KTC", "LH", "MINT",
    "MTC", "OR", "OSP", "PTT", "PTTEP", "PTTGC", "RATCH", "SAWAD", "SCB", "SCC",
    "SCGP", "TCAP", "TIDLOR", "TISCO", "TLI", "TOP", "TRUE", "TTB", "TU", "WHA"
]

def get_json_filepath() -> Path:
    """Returns the absolute path to the local set50_shareholders.json file."""
    return Path(__file__).parent / "set50_shareholders.json"

def fetch_all_shareholders() -> list:
    """Fetch all saved shareholder data from the local JSON file."""
    filepath = get_json_filepath()
    if not filepath.exists():
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error reading local JSON file: {e}")
        return []

def save_shareholders(symbol: str, shareholders: list, book_close_date: str):
    """Save top 5 shareholders to the local JSON file, replacing previous records for the symbol."""
    filepath = get_json_filepath()
    
    # Load existing records
    existing_records = fetch_all_shareholders()
    
    # Filter out old records for the symbol to prevent duplicates
    filtered_records = [r for r in existing_records if r.get("symbol") != symbol]
    
    # Format new records
    new_records = []
    for sh in shareholders[:5]:
        new_records.append({
            "symbol": symbol,
            "sequence": sh.get("sequence"),
            "name": sh.get("name"),
            "shares": sh.get("numberOfShare"),
            "percent": sh.get("percentOfShare"),
            "book_close_date": book_close_date,
            "updated_at": datetime.now().isoformat()
        })
    
    # Append new records
    filtered_records.extend(new_records)
    
    # Write back to JSON file (with Thai characters readable)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(filtered_records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing to JSON file: {e}")
        raise e

def get_scraper_session() -> requests.Session:
    """Create a requests Session initialized with cookies from the SET website to bypass security walls."""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    session.headers.update(headers)
    # Perform a dummy request to establish Incapsula/session cookies
    try:
        session.get("https://www.set.or.th/th/market/product/stock/quote/ADVANC/major-shareholders", timeout=10)
    except Exception as e:
        print(f"Warning: Failed to initialize session cookies: {e}")
    return session

def scrape_symbol_shareholders(session: requests.Session, symbol: str) -> tuple:
    """Scrape major shareholders for a symbol using the established session.
    
    Returns (shareholders_list, book_close_date)
    """
    url = f"https://www.set.or.th/api/set/stock/{symbol}/shareholder?lang=th"
    api_headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.set.or.th/th/market/product/stock/quote/{symbol}/major-shareholders",
    }
    
    response = session.get(url, headers=api_headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        book_close_date = data.get("bookCloseDate", "")
        # Format bookCloseDate nicely if it is ISO format
        if book_close_date and "T" in book_close_date:
            book_close_date = book_close_date.split("T")[0]
        major_shareholders = data.get("majorShareholders", [])
        return major_shareholders, book_close_date
    elif response.status_code == 404:
        raise ValueError(f"Symbol {symbol} not found on SET.")
    else:
        raise RuntimeError(f"Failed to fetch. Status code: {response.status_code}")
