from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.htm')

@app.route('/scrape', methods=['POST'])
def scrape():
    # Extract the URL from the request
    data = request.json
    url = data.get('url')

    # Check if the URL is not empty
    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        # Fetch the content of the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find bullet points related to "Scholarship" and their URLs
        points = []
        for li in soup.find_all('li'):
            if 'scholarship' in li.text.lower():
                link = li.find('a', href=True)
                if link:
                    # Convert relative URL to absolute URL
                    absolute_url = urljoin(url, link['href'])
                    points.append({'text': li.text.strip(), 'url': absolute_url})
                else:
                    # If there is no link, return None for the URL
                    points.append({'text': li.text.strip(), 'url': None})

        # Return the found points with URLs
        return jsonify({'points': points})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

