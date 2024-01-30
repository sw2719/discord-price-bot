import asyncio
import os
import re
import aiohttp

from typing import Union, Tuple
from bs4 import BeautifulSoup

from services.base import AbstractService, BaseServiceItem, USER_AGENT, TIMEOUT


def pprint(*args, **kwargs):
    print('[univstore]', *args, **kwargs)


class UnivStoreItem(BaseServiceItem):
    def __init__(self, **kwargs):
        univstore_dict = {
            'name': {'label': '상품명', 'type': str, 'value': ''},
            'price': {'label': '가격', 'type': str, 'value': ''},
            'stock': {'label': '재고', 'type': str, 'value': ''},
            'thumbnail': {'type': str, 'value': ''}
        }

        super().__init__(univstore_dict, **kwargs)


class UnivStoreService(AbstractService):
    SERVICE_DEFAULT_CONFIG = {
        'login': False,
        'id': '',
        'password': ''
    }
    SERVICE_NAME = 'univstore'
    SERVICE_LABEL = '학생복지스토어'
    SERVICE_COLOR = 0xea5b5d
    SERVICE_ICON = 'https://univstore.com/image/favicon.png'

    def __init__(self, cfg):
        self.headers = {'User-Agent': USER_AGENT}
        self.LOGIN = cfg['login']
        self.UNIVSTORE_ID = cfg['id']
        self.UNIVSTORE_PASSWORD = cfg['password']

        if not self.LOGIN:
            pprint("Warning: login is disabled. "
                   "Price data is not available.")
            self.jar = None
        else:
            self.jar = aiohttp.CookieJar()
            if os.path.isfile('cookies/univstore'):
                pprint('Loading saved cookie...')
                self.jar.load('cookies/univstore')

        pprint('univstore service initialized.')

    async def standardize_url(self, url: str) -> Union[str, None]:
        if re.match('https://univstore.com/item/[0-9]+', url):
            return url
        else:
            return None

    async def _login(self, session):
        await session.get('https://univstore.com/')
        async with session.get('https://univstore.com/user/login') as r:
            if 'login' in str(r.url):
                pprint("Autologin cookie doesn't exist or has expired. Logging in...")
                # Login POST data schema
                # userid: Username
                # password: Password
                # autologin: 1 for true, 0 for false
                data = {'userid': self.UNIVSTORE_ID, 'password': self.UNIVSTORE_PASSWORD, 'autologin': '1'}
                await session.post('https://univstore.com/api/user/login', data=data)

        self.jar.save('cookies/univstore')

    async def fetch_items(self, url_list: list) -> dict:
        async with aiohttp.ClientSession(headers=self.headers, cookie_jar=self.jar, timeout=TIMEOUT) as session:
            if self.LOGIN:
                await self._login(session)
            results = await asyncio.gather(*[self.get_product_info(url, session) for url in url_list])

        result_dict = {}

        for result in results:
            result_dict[result[0]] = result[1]

        return result_dict

    async def get_product_info(self, url: str, session: aiohttp.ClientSession = None) -> Tuple[str, UnivStoreItem]:
        if not session:
            async with aiohttp.ClientSession(headers=self.headers, cookie_jar=self.jar, timeout=TIMEOUT) as session:
                if self.LOGIN:
                    await self._login(session)
                return await self.get_product_info(url, session)

        async with session.get(url) as r:
            text = await r.text()
            r.raise_for_status()

        soup = BeautifulSoup(text, 'html.parser')

        thumbnail = soup.find('div', class_='swiper-slide swiper-lazy')['data-background']
        item_name = soup.select_one(
            'body > main > div.usItemAreaTop > div > div.usItemCardController > div.usItemCardInfo > div.usItemCardInfoName > a > span').string

        if self.LOGIN:
            item_price = soup.select_one(
                'body > main > div.usItemAreaTop > div > div.usItemCardController > div.usItemCardInfo > div.usItemCardInfoPrice2').string

            if soup.select_one(
                    'body > main > div.usItemAreaTop > div > div.usItemCardController > div.usItemCardInfo > div.usOutofstockMessage'):
                stock = '품절'
            else:
                stock = '재고 있음'
        else:
            item_price = '로그인 필요'
            stock = '로그인 필요'

        item = UnivStoreItem(
            name=str(item_name),
            price=str(item_price) + '원',
            stock=stock,
            thumbnail=str(thumbnail)
        )

        return url, item
