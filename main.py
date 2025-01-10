from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import json
import re
import os
from datetime import datetime

# ==========================
# Configuration and Setup
# ==========================

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all levels of log messages
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named app.log
        logging.StreamHandler()  # Also log to the console
    ]
)

# Initialize Flask app
app = Flask(__name__)

# Define constants
OUTPUT_DIR = 'output'
JSON_OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'scholarships.json')

# Ensure the output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    logging.info(f"Created output directory at {OUTPUT_DIR}")

# ==========================
# Utility Functions
# ==========================

def validate_url(url):
    """
    Validate the provided URL to ensure it is properly formatted.
    Args:
        url (str): The URL to validate.
    Returns:
        bool: True if URL is valid, False otherwise.
    """
    logging.debug("Validating URL...")
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https:// or ftp://
        r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
        r'(?:(?:[A-Z0-9-]+\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}(?:\.\d{1,3}){3})'  # ...or IPv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    is_valid = re.match(regex, url) is not None
    logging.debug(f"URL validation result for '{url}': {is_valid}")
    return is_valid

def fetch_page_content(url):
    """
    Fetch the content of a URL and return the parsed BeautifulSoup object.
    Args:
        url (str): The URL to fetch.
    Returns:
        BeautifulSoup: Parsed HTML content.
    Raises:
        requests.exceptions.RequestException: If the request fails.
    """
    try:
        logging.info(f"Fetching content from URL: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        logging.debug(f"Successfully fetched content from {url}")
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching content from {url}: {e}")
        raise

def extract_scholarship_data(soup, base_url):
    """
    Extract scholarship-related list items and their URLs from the BeautifulSoup object.
    Args:
        soup (BeautifulSoup): Parsed HTML content.
        base_url (str): The base URL to resolve relative links.
    Returns:
        list: A list of dictionaries containing scholarship text and URLs.
    """
    logging.info("Extracting scholarship-related data...")
    points = []
    list_items = soup.find_all('li')
    logging.debug(f"Found {len(list_items)} list items on the page.")

    for index, li in enumerate(list_items, start=1):
        text = li.get_text(separator=' ', strip=True)
        if 'scholarship' in text.lower():
            link = li.find('a', href=True)
            if link:
                absolute_url = urljoin(base_url, link['href'])
                points.append({'text': text, 'url': absolute_url})
                logging.debug(f"List item {index}: Found scholarship with URL {absolute_url}")
            else:
                points.append({'text': text, 'url': None})
                logging.debug(f"List item {index}: Found scholarship without a URL")
    
    logging.info(f"Total scholarships found: {len(points)}")
    return points

def save_to_json(data, filename=JSON_OUTPUT_FILE):
    """
    Save the scraped data to a JSON file.
    Args:
        data (list): The data to save.
        filename (str): The file path to save the data.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        logging.info(f"Successfully saved data to {filename}")
    except IOError as e:
        logging.error(f"Failed to save data to {filename}: {e}")

def sanitize_input(url):
    """
    Sanitize the input URL to prevent potential security issues.
    Args:
        url (str): The URL to sanitize.
    Returns:
        str: The sanitized URL.
    """
    parsed_url = urlparse(url)
    sanitized = parsed_url.geturl()
    logging.debug(f"Sanitized URL: {sanitized}")
    return sanitized

# ==========================
# Route Handlers
# ==========================

@app.route('/')
def home():
    """
    Render the home page.
    Returns:
        Rendered HTML template.
    """
    logging.info("Serving the home page.")
    return render_template('index.htm')

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Endpoint to scrape scholarship-related information from a given URL.
    Expects a JSON payload with a 'url' field.
    Returns:
        JSON response with scraped scholarship data or error message.
    """
    logging.info("Scrape endpoint accessed.")
    data = request.get_json()

    if not data:
        logging.warning("No JSON payload received in the request.")
        return jsonify({'error': 'Invalid request. JSON payload expected.'}), 400

    url = data.get('url')
    if not url:
        logging.warning("No URL provided in the request.")
        return jsonify({'error': 'Missing URL'}), 400

    sanitized_url = sanitize_input(url)
    if not validate_url(sanitized_url):
        logging.warning(f"Invalid URL format provided: {sanitized_url}")
        return jsonify({'error': 'Invalid URL format'}), 400

    try:
        soup = fetch_page_content(sanitized_url)
        points = extract_scholarship_data(soup, sanitized_url)

        if points:
            save_to_json(points)  # Save results to a JSON file
            logging.info("Returning scraped scholarship data.")
            return jsonify({'points': points}), 200
        else:
            logging.info("No scholarships found on the provided URL.")
            return jsonify({'points': [], 'message': 'No scholarships found.'}), 200

    except Exception as e:
        logging.exception("An unexpected error occurred during scraping.")
        return jsonify({'error': 'An error occurred while scraping the URL.'}), 500

# ==========================
# Additional Routes (Optional)
# ==========================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify if the server is running.
    Returns:
        JSON response indicating server status.
    """
    logging.info("Health check endpoint accessed.")
    return jsonify({'status': 'Server is running.'}), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Endpoint to retrieve the latest logs.
    Returns:
        JSON response with the last 100 lines of the log file.
    """
    try:
        with open('app.log', 'r') as log_file:
            lines = log_file.readlines()
            last_lines = lines[-100:]  # Get the last 100 lines
        logging.info("Logs retrieved successfully.")
        return jsonify({'logs': ''.join(last_lines)}), 200
    except IOError as e:
        logging.error(f"Failed to read log file: {e}")
        return jsonify({'error': 'Unable to retrieve logs.'}), 500

# ==========================
# Error Handlers
# ==========================

@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors.
    Args:
        error: The error that occurred.
    Returns:
        JSON response with error message.
    """
    logging.warning(f"404 error encountered: {error}")
    return jsonify({'error': 'Resource not found.'}), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors.
    Args:
        error: The error that occurred.
    Returns:
        JSON response with error message.
    """
    logging.error(f"500 error encountered: {error}")
    return jsonify({'error': 'Internal server error.'}), 500

# ==========================
# Main Entry Point
# ==========================

if __name__ == '__main__':
    logging.info("Starting the Flask application...")
    app.run(debug=True)
