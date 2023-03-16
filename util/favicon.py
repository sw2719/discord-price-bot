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


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'

print(get_favicon('https://www.danawa.com/', headers={'User-Agent': USER_AGENT}))