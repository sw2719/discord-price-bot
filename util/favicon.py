import requests
from bs4 import BeautifulSoup


def get_favicon(url, headers=None):
    """Retrieves the favicon URL of a website."""
    if headers is None:
        headers = {}
    try:
        response = requests.get(url, headers=headers)
        html = response.content

        soup = BeautifulSoup(html, 'html.parser')
        favicon_link = soup.find('link', rel='icon')

        if favicon_link is not None:
            favicon_url = favicon_link['href']
            if favicon_url.startswith('//'):
                favicon_url = f'{url.split("//")[0]}{favicon_url}'
            return favicon_url

        return ''

    except requests.RequestException:
        return ''
