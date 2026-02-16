# Data Scraper Project

This is a Django-based web application that scrapes data based on Category, City, and Country inputs.
Currently, it uses DuckDuckGo HTML search as the data source.

## Setup

1. Install dependencies:
   ```bash
   pip install django beautifulsoup4 requests
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Start the server:
   ```bash
   python manage.py runserver
   ```

4. Access the application at `http://127.0.0.1:8000`.

## Features

- **Search Form**: Input Category, City, and Country.
- **Scraping**: Fetches results from DuckDuckGo HTML version.
- **Download**: Export results to CSV.

## Customization

To scrape a different website, modify the `perform_scraping` function in `scraper_app/views.py`.
