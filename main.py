from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import json
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)

def validate_url(url):
    """
    Validate the provided URL to ensure it is properly formatted.
    """
    logging.debug("Validating URL...")
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)'  # domain...
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def fetch_page_content(url):
    """
    Fetch the content of a URL and return the parsed BeautifulSoup object.
    """
    try:
        logging.info(f"Fetching content from URL: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching content: {e}")
        raise

def extract_scholarship_data(soup, base_url):
    """
    Extract scholarship-related list items and their URLs.
    """
    logging.info("Extracting scholarship-related data...")
    points = []
    for li in soup.find_all('li'):
        if 'scholarship' in li.text.lower():
            link = li.find('a', href=True)
            if link:
                absolute_url = urljoin(base_url, link['href'])
                points.append({'text': li.text.strip(), 'url': absolute_url})
            else:
                points.append({'text': li.text.strip(), 'url': None})
    logging.debug(f"Found {len(points)} scholarship entries.")
    return points

@app.route('/')
def home():
    """
    Render the home page.
    """
    logging.info("Serving the home page.")
    return render_template('index.htm')

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Endpoint to scrape scholarship-related information from a given URL.
    """
    logging.info("Scrape endpoint hit.")
    data = request.json
    url = data.get('url')

    if not url:
        logging.warning("No URL provided in request.")
        return jsonify({'error': 'Missing URL'}), 400

    if not validate_url(url):
        logging.warning(f"Invalid URL provided: {url}")
        return jsonify({'error': 'Invalid URL format'}), 400

    try:
        soup = fetch_page_content(url)
        points = extract_scholarship_data(soup, url)

        # Optionally save results to a file
        with open('scholarships.json', 'w') as file:
            json.dump(points, file, indent=4)

        return jsonify({'points': points})
    except Exception as e:
        logging.exception("An error occurred during scraping.")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logging.info("Starting the Flask app...")
    app.run(debug=True)
