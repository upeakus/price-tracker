# Price Tracker

A small Python web scraper that watches product prices. It saves every price to SQLite, tells you when a price **drops** or reaches your **target**, and can export the history to CSV for Excel.

- Works with any shop page: you give a URL and a CSS selector
- Understands formats like 1 299,90 MDL and $1,299.90
- One broken page never stops the others
- Optional Telegram alerts (token stays in environment variables)

## Install

```bash
pip install -r requirements.txt
```

## Config

Copy config.example.json to config.json and list your products:

```json
{
  "products": [
    {
      "name": "Phone",
      "url": "https://shop.example/phone",
      "selector": ".price",
      "target": 500
    }
  ]
}
```

How to find the selector: open the product page in Chrome, right click the price, choose Inspect, then right click the highlighted element and choose Copy, Copy selector.

## Run

```bash
python3 tracker.py config.json
```

Run it every hour with cron:

```bash
0 * * * * cd /path/to/price-tracker && python3 tracker.py config.json
```

Export the history to CSV:

```bash
python3 tracker.py config.json --export prices.csv
```

## Telegram alerts (optional)

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"
```

Without these variables, alerts are just printed to the console.

## Notes

Check the rules (robots.txt and terms) of the site before scraping it, and keep the check interval reasonable.

## License

MIT
