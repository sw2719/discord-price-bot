import re
import asyncio
import aiohttp
from typing import Union, Tuple
from furl import furl
from bs4 import BeautifulSoup
from services.base import AbstractService, BaseServiceItem, USER_AGENT
from util.favicon import get_favicon


def pprint(*args, **kwargs):
    print('[coupang]', *args, **kwargs)


class CoupangItem(BaseServiceItem):
    def __init__(self, **kwargs):
        coupang_dict = {
            'name': {'label': '상품명', 'type': str, 'value': ''},
            'option': {'type': dict, 'value': {}},
            'price': {'label': '가격', 'type': str, 'value': ''},
            'quantity': {'label': '재고', 'type': str, 'value': ''},
            'card_benefits': {'label': '카드 할인', 'type': dict, 'value': {}},
            'preorder': {'label': '사전예약', 'type': str, 'value': '사전예약 중 아님'},
            'thumbnail': {'type': str, 'value': ''}
        }

        super().__init__(coupang_dict, **kwargs)


class CoupangService(AbstractService):
    SERVICE_DEFAULT_CONFIG = {
        'use_wow_price': False,
        'login': False,
        'email': '',
        'password': ''
    }
    SERVICE_NAME = 'coupang'
    SERVICE_LABEL = '쿠팡'
    SERVICE_COLOR = 0xC73D33

    def __init__(self, cfg):
        self.USE_WOW_PRICE = cfg['use_wow_price']
        self.LOGIN = cfg['login']

        self.EMAIL = cfg['email']
        self.PASSWORD = cfg['password']

        self.header = {
            'user-agent': USER_AGENT,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ko-KR,ko;q=0.9',
            'connection': 'keep-alive',
            'cache-control': 'max-age=0',
            'upgrade-insecure-requests': '1'
        }

        self.login_header = {
            'user-agent': USER_AGENT,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ko-KR,ko;q=0.9',
            'connection': 'keep-alive',
            'cache-control': 'max-age=0',
            'upgrade-insecure-requests': '1',
            'Host': 'login.coupang.com',
            'Referer': 'https://login.coupang.com/login/login.pang'
        }

        #self.SERVICE_ICON = get_favicon('https://www.coupang.com/', headers=self.header)
        self.SERVICE_ICON = 'https://image9.coupangcdn.com/image/coupang/favicon/v2/favicon.ico'
        pprint('Coupang service initialized.')

    async def standardize_url(self, input_string: str) -> Union[str, None]:
        """Standardize given Coupang URL to www.coupang.com/vp/products/... format.
           Returns None if URL is invalid or exception occurs."""

        try:
            if 'm.coupang.com' in input_string:
                url = input_string.replace('m.', 'www.').replace('vm', 'vp')

            elif input_string.startswith('쿠팡을 추천합니다!'):
                url = input_string.split('\n')[2]

                async with aiohttp.ClientSession(headers=self.header) as session:
                    async with session.get(url, headers=self.header) as r:
                        f = furl(r.url)

                        page_value = f.args['pageValue']
                        item_id = f.args['itemId']
                        vendor_item_id = f.args['vendorItemId']

                url = f'https://www.coupang.com/vp/products/{page_value}?itemId={item_id}&vendorItemId={vendor_item_id}'

            elif 'link.coupang.com' in input_string:
                f = furl(input_string)

                page_value = f.args['pageValue']
                item_id = f.args['itemId']
                vendor_item_id = f.args['vendorItemId']

                url = f'https://www.coupang.com/vp/products/{page_value}?itemId={item_id}&vendorItemId={vendor_item_id}'

            elif 'www.coupang.com/vp/products/' in input_string:
                f = furl(input_string)

                page_value = [string for string in re.findall('[0-9]*', input_string.split('?')[0]) if string][0]
                item_id = f.args['itemId']
                vendor_item_id = f.args['vendorItemId']

                url = f'https://www.coupang.com/vp/products/{page_value}?itemId={item_id}&vendorItemId={vendor_item_id}'

            else:
                return None

            return url
        except aiohttp.ClientError:
            pprint(f'Error while standardizing Coupang URL/string: {input_string}')
            return None

    async def fetch_items(self, url_list: list) -> dict:
        async with aiohttp.ClientSession(headers=self.header) as session:
            if self.LOGIN:
                await self._login(session)
            results = await asyncio.gather(*[self.get_product_info(url, session) for url in url_list])

        result_dict = {}

        for result in results:
            result_dict[result[0]] = result[1]

        return result_dict

    async def get_product_info(self, url: str, session: aiohttp.ClientSession = None) -> Tuple[str, CoupangItem]:
        # TODO: Rewrite this disaster
        if not session:
            async with aiohttp.ClientSession(headers=self.header) as session:
                return await self.get_product_info(url, session)

        async with session.get(url) as r:
            text = await r.text()
            r.raise_for_status()

        soup = BeautifulSoup(text, 'html.parser')

        price_match = soup.select('span.total-price > strong')
        item_match = soup.find_all('h2', class_='prod-buy-header__title')

        item_name = re.sub('<[^<>]*>', '', str(item_match[0]))

        option_names = [re.sub('<[^<>]*>', '', str(option_name)) for option_name in
                        soup.find_all('span', class_='title')]
        option_values = [re.sub('<[^<>]*>', '', str(option_value)) for option_value in
                         soup.find_all('span', class_='value')]

        option = {}

        for x in range(len(option_names)):
            option[option_names[x]] = option_values[x]

        if not price_match:
            current_price = 0

        else:
            if self.USE_WOW_PRICE:
                try:
                    price_output = [element for element in re.split('<[^<>]*>', str(price_match[1])) if
                                    element.strip()]
                    if price_output == ['원']:
                        raise IndexError

                except IndexError:
                    price_output = [element for element in re.split('<[^<>]*>', str(price_match[0])) if
                                    element.strip()]

            else:
                price_output = [element for element in re.split('<[^<>]*>', str(price_match[0])) if
                                element.strip()]

            current_price = int(re.sub('[^0-9]', '', price_output[0]))

        current_price = f'{current_price:,}원'

        card_benefits = {}
        if soup.find('span', class_='benefit-label'):
            rates = []

            for element in soup.find_all('span', class_='benefit-label'):
                rate = ''.join(filter(str.isdigit, str(element)))

                rates.append(f'{rate}%')

            card_sets = []

            for benefit_badge in soup.find_all('div', class_='ccid-benefit-badge__inr'):
                card_set = []
                for element in benefit_badge.contents:
                    if element.name == 'img':
                        img_src = element['src']
                        if 'hana-sk' in img_src:
                            card_set.append('하나')
                        elif 'kb' in img_src:
                            card_set.append('국민')
                        elif 'lotte' in img_src:
                            card_set.append('롯데')
                        elif 'shinhan' in img_src:
                            card_set.append('신한')
                        elif 'hyundai' in img_src:
                            card_set.append('현대')
                        elif 'woori' in img_src:
                            card_set.append('우리')
                        elif 'samsung' in img_src:
                            card_set.append('삼성')
                        elif 'bc' in img_src:
                            card_set.append('BC')
                card_sets.append(card_set)

            for i in range(len(rates)):
                card_benefits[', '.join(card_sets[i])] = rates[i]

        if soup.find('div', class_='aos-label'):
            qty = re.sub(r'<[^<>]*>', '', str(soup.find('div', class_='aos-label')))
        elif soup.find('div', class_='oos-label'):
            qty = '품절'
            current_price += ' (품절)'
        else:
            qty = '재고 있음'

        if soup.find('span', class_='prod-pre-order-badge-text').string:
            preorder = '사전예약 중'
        else:
            preorder = '사전예약 중 아님'

        thumbnail = soup.find('img', class_='prod-image__detail')
        thumbnail = f"https:{thumbnail['src']}"

        item = CoupangItem(
            name=item_name,
            price=current_price,
            option=option,
            quantity=qty,
            card_benefits=card_benefits,
            preorder=preorder,
            thumbnail=thumbnail
        )
        return url, item

    async def _login(self, session: aiohttp.ClientSession):
        post_data = {'email': self.EMAIL,
                     'password': self.PASSWORD,
                     'rememberMe': 'false'}

        await session.get('https://login.coupang.com/login/login.pang')
        await session.post('https://login.coupang.com/login/loginProcess.pang',
                           headers=self.login_header,
                           data=post_data)


if __name__ == '__main__':
    coupang = CoupangService({
        'use_wow_price': True,
        'login': False,
        'email': '',
        'password': '',
    })

    print('Coupang module test')
    test_url = input('Enter coupang URL: ')
    standardized_test_url = asyncio.run(coupang.standardize_url(test_url))
    print('Standardized URL:', standardized_test_url)
    _, test_item = asyncio.run(coupang.get_product_info(standardized_test_url))

    for key, value in test_item.items():
        print(key, '-', value)
