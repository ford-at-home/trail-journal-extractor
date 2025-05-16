import requests
from bs4 import BeautifulSoup
import sys
import time
import re

def extract_entry(url, headers):
    print(f"Fetching entry: {url}")
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # Extract meta title as fallback title
    meta_title = soup.title.text.strip() if soup.title else "Untitled"
    date_tag = soup.select_one("div.entry-date")
    entry_text = soup.select_one("div.entry")

    # Structured fields
    def get_label_value(label):
        span = soup.find("span", string=re.compile(f"{label}:"))
        return span.find_next("span").text.strip() if span else "N/A"

    entry = {
        "url": url,
        "title": meta_title,
        "date": date_tag.text.strip() if date_tag else "Unknown Date",
        "destination": get_label_value("Destination"),
        "start_location": get_label_value("Start Location"),
        "miles_today": get_label_value("Today's Miles"),
        "trip_miles": get_label_value("Trip Miles"),
        "body": entry_text.get_text(separator="\n").strip() if entry_text else "[No content found]"
    }

    print(f"✅ Parsed: {entry['date']} | {entry['destination']}")
    return entry

def build_journal(journal_id):
    base_url = "https://www.trailjournals.com"
    entries_url = f"{base_url}/journal/entries/{journal_id}"
    headers = {"User-Agent": "Mozilla/5.0"}

    print(f"🔍 Loading entry list for journal ID {journal_id}...")
    res = requests.get(entries_url, headers=headers)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    entry_urls = [
        f"{base_url}{opt['value']}"
        for opt in soup.select("select[name='guidelinks'] option")
        if opt.get("value", "").startswith("/journal/entry/")
    ]

    print(f"📄 Found {len(entry_urls)} entries. Starting download...\n")
    output_file = f"journal_{journal_id}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        for i, url in enumerate(entry_urls, 1):
            print(f"[{i}/{len(entry_urls)}] Processing {url}")
            try:
                entry = extract_entry(url, headers)
                f.write(f"# {entry['date']} — {entry['destination']}\n")
                f.write(f"**Start Location:** {entry['start_location']}\n")
                f.write(f"**Miles Today:** {entry['miles_today']}\n")
                f.write(f"**Trip Miles:** {entry['trip_miles']}\n\n")
                f.write(f"{entry['body']}\n")
                f.write("\n---\n\n")
            except Exception as e:
                print(f"⚠️ Error on {url}: {e}")
            time.sleep(0.2)  # Be kind to the server

    print(f"\n✅ All entries saved to {output_file}")

# Only run if triggered via CLI
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_journal.py <journal_id>")
        sys.exit(1)
    build_journal(sys.argv[1])
