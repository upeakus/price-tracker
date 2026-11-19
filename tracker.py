#!/usr/bin/env python3
"""
Price Tracker - a small web scraper.

What it does:
  * Opens product pages listed in config.json.
  * Finds the price on each page with a CSS selector.
  * Saves every price to a SQLite database (history).
  * Prints a Telegram-ready alert when the price DROPS (optional Telegram send).
  * Can export the whole history to a CSV file (opens in Excel).

Usage:
  python tracker.py config.json            # check all products once
  python tracker.py config.json --export prices.csv   # save history to CSV
"""

import csv
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

import requests                 # downloads web pages
from bs4 import BeautifulSoup   # reads HTML and finds elements

import json

DB_FILE = "prices.db"
# Pretend to be a normal browser, some sites block the default Python agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def init_db(path):
    """Create the table for price history if it does not exist."""
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            url TEXT NOT NULL,
            checked_at TEXT NOT NULL      -- UTC time, ISO format
        )
        """
    )
    conn.commit()
    return conn


def parse_price(text):
    """Turn text like '1 299,90 MDL' or '$1,299.90' into the number 1299.9."""
    # Keep only digits, dots, commas and spaces.
    cleaned = re.sub(r"[^\d.,]", "", text.replace("\xa0", ""))
    if not cleaned:
        raise ValueError("no digits in: " + repr(text))
    # If both separators exist, the LAST one is the decimal separator.
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")   # 1.299,90
        else:
            cleaned = cleaned.replace(",", "")                     # 1,299.90
    elif "," in cleaned:
        # '12,50' is a decimal comma, '1,299' is a thousands separator.
        head, _, tail = cleaned.rpartition(",")
        cleaned = head.replace(",", "") + "." + tail if len(tail) != 3 else cleaned.replace(",", "")
    return float(cleaned)


def fetch_price(url, selector):
    """Download the page, find the element by CSS selector, return its price."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()               # raise an error on 404 / 500
    soup = BeautifulSoup(response.text, "html.parser")
    element = soup.select_one(selector)       # first element matching selector
    if element is None:
        raise ValueError("selector not found: " + selector)
    return parse_price(element.get_text(strip=True))


def last_price(conn, name):
    """Return the previous saved price for a product, or None."""
    row = conn.execute(
        "SELECT price FROM prices WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)
    ).fetchone()
    return None if row is None else row[0]


def notify(text):
    """Send to Telegram if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set, else print."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    print(text)
    if token and chat_id:
        try:
            requests.post("https://api.telegram.org/bot" + token + "/sendMessage",
                          data={"chat_id": chat_id, "text": text}, timeout=10)
        except requests.RequestException:
            print("Could not reach Telegram")   # never print the URL: it has the token


def check_all(config, conn):
    """Check every product in the config and report price drops."""
    for item in config["products"]:
        name = item["name"]
        try:
            price = fetch_price(item["url"], item["selector"])
        except Exception as exc:               # one broken page must not stop the rest
            print("ERROR " + name + ": " + str(exc))
            continue

        previous = last_price(conn, name)
        conn.execute(
            "INSERT INTO prices (name, price, url, checked_at) VALUES (?, ?, ?, ?)",
            (name, price, item["url"], datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()

        print(name + ": " + str(price))
        # Alert on a drop, or when the price is under the user's target price.
        if previous is not None and price < previous:
            notify("PRICE DROP: " + name + "\n" + str(previous) + " -> " + str(price) + "\n" + item["url"])
        elif "target" in item and price <= item["target"]:
            notify("TARGET REACHED: " + name + " costs " + str(price) + "\n" + item["url"])


def export_csv(conn, path):
    """Write the whole history to a CSV file."""
    rows = conn.execute("SELECT name, price, url, checked_at FROM prices ORDER BY id").fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "price", "url", "checked_at"])
        writer.writerows(rows)
    print("Saved " + str(len(rows)) + " rows to " + path)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    with open(args[0], encoding="utf-8") as f:
        config = json.load(f)
    conn = init_db(config.get("db_file", DB_FILE))
    if "--export" in args:
        export_csv(conn, args[args.index("--export") + 1])
    else:
        check_all(config, conn)


if __name__ == "__main__":
    main()
