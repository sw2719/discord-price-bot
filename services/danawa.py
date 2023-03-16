import logging
import asyncio
import aiohttp
import ssl
from typing import Union, Tuple
from furl import furl
from bs4 import BeautifulSoup
from services.base import BaseService, BaseServiceItem, USER_AGENT
from util.favicon import get_favicon

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT


class DanawaItem(BaseServiceItem):
    def __init__(self, **kwargs):
        danawa_dict = {
            'name': {'label': '상품명', 'type': str, 'value': ''},
            'price': {'label': '최저가', 'type': str, 'value': ''},
            'card_price': {'label': '카드 최저가', 'type': str, 'value': ''},
            'thumbnail': {'type': str, 'value': ''}
        }

        super().__init__(danawa_dict, **kwargs)


class DanawaService(BaseService):
    SERVICE_DEFAULT_CONFIG = None
    SERVICE_NAME = 'danawa'
    SERVICE_LABEL = '다나와'
    SERVICE_COLOR = 0x5EC946
    SERVICE_ICON = 'https://img.danawa.com/new/tour/img/logo/sns_danawa.jpg'
    def __init__(self):
        logger.info('Danawa service initialized.')

    async def standardize_url(self, url: str) -> Union[str, None]:
        if 'danawa.page.link' in url:  # Mobile App Share URL to Mobile Web URL
            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=context) as r:
                    url = str(r.url)

        f = furl(url)

        if 'prod.danawa.com' in url:  # PC URL
            url = f'https://prod.danawa.com/info/?pcode={f.args["pcode"]}'
        elif 'm.danawa.com/product' in url:  # Mobile URL
            url = f'https://prod.danawa.com/info/?pcode={f.args["code"]}'

        return url

    async def fetch_items(self, url_list: list) -> dict:
        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(*[self.get_product_info(url, session) for url in url_list])

        result_dict = {}

        for result in results:
            result_dict[result[0]] = result[1]

        return result_dict

    async def get_product_info(self, url: str, session: aiohttp.ClientSession = None) -> Tuple[str, DanawaItem]:
        if not session:
            async with aiohttp.ClientSession() as session:
                return await self.get_product_info(url, session)

        async with session.get(url, ssl=context) as r:
            text = await r.text()
            r.raise_for_status()

        soup = BeautifulSoup(text, 'html.parser')

        prod_name = str(soup.select_one('#blog_content > div.summary_info > div.top_summary > h3 > span').contents[0])
        thumbnail = f"https:{soup.find('img', id='baseImage')['src']}"

        txt_no = soup.select_one(
            '#blog_content > div.summary_info > div.detail_summary > div.summary_left > div.lowest_area > div.no_data > p > strong'
        )

        if txt_no:
            price = txt_no.string
            card_price = ''
        else:
            price = soup.select_one(
                'div.lowest_area > div.lowest_top > div.row.lowest_price > span.lwst_prc > a > em'
            )
            price = f'{price.string}원'
            card_price = soup.select_one(
                'div.lowest_area > div.lowest_list > table > tbody.card_list > tr > td.price > a > span.txt_prc > em'
            )

            if card_price:
                card_price_card = soup.select_one(
                    'div.lowest_area > div.lowest_list > table > tbody.card_list > tr > td.price > a > span.txt_dsc'
                )
                card_price_card = card_price_card.contents[0]
                card_price = f'{card_price.contents[0]}원 ({card_price_card})'
            else:
                card_price = ''

        item = DanawaItem(
            name=prod_name,
            price=price,
            card_price=card_price,
            thumbnail=thumbnail
        )

        return url, item

