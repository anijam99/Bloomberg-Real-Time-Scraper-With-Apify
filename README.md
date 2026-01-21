# Bloomberg Real-Time Article Scraper with Apify

A Python pipeline that continuously scrapes Bloomberg news articles using Apify's Bloomberg Article Scraper actor. Supports real-time continuous scraping via the Bloomberg sitemap and single-article mode for one-off scrapes.

## Features

- **Real-Time Mode**: Continuously polls Bloomberg's news sitemap for new articles
- **Single-Article Mode**: Scrape a specific article URL on demand
- **URL Deduplication**: Tracks scraped URLs to avoid duplicate processing
- **Configurable**: All settings via environment variables
- **Persistence**: Optional JSON file to persist scraped URLs between sessions

## Prerequisites

- An [Apify account](https://apify.com/) with API access
- Apify API token (free tier available)

## Installation

1. **Clone or download this repository**

   ```bash
   git clone https://github.com/anijam99/Bloomberg-Real-Time-Scraper-With-Apify.git
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your settings (see Configuration section)
   ```

## Configuration

Create a `.env` file with the following settings:

```env
# REQUIRED: Your Apify API token
APIFY_API_TOKEN=your_apify_token_here

# Scraping mode: 'realtime' or 'single'
SCRAPE_MODE=realtime

# Maximum URLs to scrape on first iteration (controls initial costs)
MAX_INITIAL_URLS=25

# How often to poll the sitemap (seconds)
POLL_INTERVAL_SECONDS=300

# URLs per Apify actor run
BATCH_SIZE=5

# Single article URL (for single mode)
SINGLE_ARTICLE_URL=

# Optional: Persist scraped URLs to file
PERSISTENCE_FILE=scraped_urls.json

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

### Getting Your Apify API Token

1. Go to [Apify Console](https://console.apify.com/)
2. Sign up or log in
3. Navigate to **Settings** → **Integrations**
4. Copy your **Personal API token**

## Usage

### Real-Time Mode

Continuously polls the Bloomberg sitemap and scrapes new articles:

```bash
python scraper.py
```

Or explicitly set the mode:

```bash
python scraper.py --mode realtime
```

The scraper will:
1. Fetch the Bloomberg news sitemap
2. Extract article URLs (limited by `MAX_INITIAL_URLS` on first run)
3. Send new URLs to the Apify actor in batches
4. Wait `POLL_INTERVAL_SECONDS` before checking for new articles
5. Repeat until stopped with Ctrl+C

### Single-Article Mode

Scrape a specific article and exit:

**Via command line:**
```bash
python scraper.py --url "https://www.bloomberg.com/news/articles/2025-01-15/example-article"
```

**Via environment variable:**
```bash
# In .env file
SCRAPE_MODE=single
SINGLE_ARTICLE_URL=https://www.bloomberg.com/news/articles/2025-01-15/example-article

# Then run
python scraper.py
```

**Via mode flag:**
```bash
python scraper.py --mode single --url "https://www.bloomberg.com/news/articles/..."
```

## Output

### Console Output

The scraper logs all activity to the console:

```
2025-01-21 10:30:00 - __main__ - INFO - Bloomberg Real-Time Article Scraper
2025-01-21 10:30:00 - __main__ - INFO - Mode: realtime
2025-01-21 10:30:01 - sitemap - INFO - Fetching sitemap from https://www.bloomberg.com/sitemaps/news/latest.xml
2025-01-21 10:30:02 - sitemap - INFO - Parsed 150 article URLs from sitemap
2025-01-21 10:30:02 - sitemap - INFO - Limited to 25 URLs (max_urls=25)
2025-01-21 10:30:02 - apify_runner - INFO - Starting Apify actor run with 5 URL(s)
2025-01-21 10:30:15 - apify_runner - INFO - Actor run completed. Dataset ID: abc123xyz
```

### Where to Find Scraped Data

Scraped article data is stored in **Apify Datasets**:

1. Go to [Apify Console](https://console.apify.com/)
2. Navigate to **Storage** → **Datasets**
3. Find datasets named with the run IDs shown in the console output
4. View, download (JSON, CSV, Excel), or export the data

Each scraped article includes:
- `title`: Article headline
- `url`: Original Bloomberg URL
- `author`: Article author(s)
- `publishedAt`: Publication date/time
- `content`: Full article text
- Additional metadata

## Rate Limits & Cost Control

### Apify Costs

The scraper uses my `jamie_tran/bloomberg-article-scraper` actor which consumes Apify compute units:

- **Free tier**: $5/month in credits (new accounts)
- **Estimated cost**: ~$0.01-0.05 per article (to be changed)

### Cost Control Settings

| Setting | Description | Recommendation |
|---------|-------------|----------------|
| `MAX_INITIAL_URLS` | Limits first batch | Start with 5-10 for testing |
| `BATCH_SIZE` | URLs per actor run | 5-10 for balance of efficiency/cost |
| `POLL_INTERVAL_SECONDS` | Time between sitemap checks | 300-600 to avoid over-polling |

### Monitoring Costs

1. Check your usage at [Apify Console](https://console.apify.com/) → **Billing**
2. Set up billing alerts in Apify settings
3. The scraper shows cost estimates before each batch

## Persistence

Enable URL persistence to remember scraped articles between sessions:

```env
PERSISTENCE_FILE=scraped_urls.json
```

This creates a JSON file tracking all scraped URLs, preventing re-scraping after restarts.

## Troubleshooting

### "APIFY_API_TOKEN is not set"

Ensure your `.env` file exists and contains a valid token:
```env
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxx
```

### "No article URL provided"

For single mode, provide a URL via:
- `--url` command line argument, OR
- `SINGLE_ARTICLE_URL` in `.env`

### "Failed to fetch sitemap"

- Check your internet connection
- Bloomberg may be blocking requests temporarily
- Try again after a few minutes

### Actor run fails repeatedly

- Verify your Apify account has available credits
- Check the actor page for any known issues
- Review Apify Console for detailed error logs

## License

This project is provided for educational and personal use. Ensure your usage complies with:
- [Bloomberg's Terms of Service](https://www.bloomberg.com/notices/tos/)
- [Apify's Terms of Service](https://apify.com/terms-of-service)

## Disclaimer

This tool is not affiliated with or endorsed by Bloomberg L.P. Use responsibly and respect rate limits and terms of service.
