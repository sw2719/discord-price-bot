import re
import asyncio
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, BrowserContext
from typing import Union, Tuple
from services.base import BaseService, BaseServiceItem, USER_AGENT
from util.favicon import get_favicon

# Debug settings
HEADLESS = True
DELAY = 0


def pprint(*args, **kwargs):
    print('[naver]', *args, **kwargs)


class NaverItem(BaseServiceItem):
    def __init__(self, **kwargs):
        naver_dict = {
            'name': {'label': '상품명', 'type': str, 'value': ''},
            'price': {'label': '가격', 'type': str, 'value': ''},
            'benefit_price': {'label': '혜택가', 'type': str, 'value': ''},
            'max_point': {'label': '최대 적립 포인트', 'type': str, 'value': ''}
        }

        super().__init__(naver_dict, **kwargs)

class NaverService(BaseService):
    SERVICE_DEFAULT_CONFIG = {
        'login': False,
        'id': '',
        'password': ''
    }
    SERVICE_NAME = 'naver'
    SERVICE_LABEL = '네이버'
    SERVICE_COLOR = 0x5ECC69
    SERVICE_ICON = get_favicon('https://www.naver.com/')

    def __init__(self, cfg):
        self.LOGIN = cfg['login']
        self.NAVER_ID = cfg['id']
        self.NAVER_PW = cfg['password']

        if not self.LOGIN:
            pprint("Warning: login is disabled. "
                   "Maximum points will be inaccurate and benefit price won't be available")
        pprint('Naver service initialized.')

    async def standardize_url(self, url) -> Union[str, None]:
        if 'naver.me' in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    url = str(r.url)

        if 'brand.naver.com' in url:
            if 'm.brand.naver.com' in url:
                url = url.replace('m.', '')
            url = re.findall('https://brand.naver.com/[a-z]*/products/[0-9]*', url)[0]
        else:
            return None

        return url

    async def _login(self, context: BrowserContext) -> None:
        main_page = await context.new_page()
        await main_page.goto('https://www.naver.com/')
        await main_page.goto('https://nid.naver.com/nidlogin.login')

        await main_page.evaluate(
            f"document.querySelector('input[id=\"id\"]').setAttribute('value', '{self.NAVER_ID}')"
        )
        await main_page.evaluate(
            f"document.querySelector('input[id=\"pw\"]').setAttribute('value', '{self.NAVER_PW}')"
        )

        await main_page.locator('#log\.login').click()
        main_page.expect_request_finished()

        try:
            await main_page.locator('#new\.save').click(timeout=2000)
        except PlaywrightTimeoutError:
            pass

    async def fetch_items(self, url_list: list) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS, slow_mo=DELAY)
            context = await browser.new_context(
                user_agent=USER_AGENT)
            await self._login(context)

            results = await asyncio.gather(*[self.get_product_info(url, context) for url in url_list])

            await context.close()
            await browser.close()

        result_dict = {}

        for result in results:
            result_dict[result[0]] = result[1]

        return result_dict

    async def get_product_info(self, url: str, context: BrowserContext = None) -> Tuple[str, NaverItem]:
        if context is None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=HEADLESS, slow_mo=DELAY)
                context = await browser.new_context(
                    user_agent=USER_AGENT)
                await self._login(context)
                url, item = await self.get_product_info(url, context)
                await context.close()
                await browser.close()

            return url, item

        product_page = await context.new_page()
        await product_page.goto(url)
        product_page.expect_request_finished()

        item_name = await product_page.locator('#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
                                               'div._3k440DUKzy > div._1eddO7u4UC > h3').text_content()

        current_price = await product_page.locator(
            '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
            'div._3k440DUKzy > div.WrkQhIlUY0 > div > strong > span._1LY7DqCnwR'
        ).text_content()
        current_price += '원'

        if self.LOGIN:
            try:
                benefit_price = await product_page.locator(
                    '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
                    'div._2a18RJADk5 > div._1UNQIwX1sN > div > strong._-2CCeRkfCX > span'
                ).text_content(timeout=1000)
                benefit_price += '원'
            except PlaywrightTimeoutError:
                benefit_price = ''
        else:
            benefit_price = ''

        max_point = await product_page.locator(
            '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
            'div._2a18RJADk5 > div._3gd5biYh9U > div > div > span',
        ).text_content()
        max_point += '원'

        item = NaverItem(
            name=item_name,
            price=current_price,
            benefit_price=benefit_price,
            max_point=max_point
        )

        return url, item


if __name__ == '__main__':
    naver = NaverService({
        'login': True,
        'id': input('Enter naver ID: '),
        'password': input('Enter naver PW: ')
    })
    print('Naver module test')
    test_url = input('Enter naver shopping URL: ')
    standardized_test_url = asyncio.run(naver.standardize_url(test_url))
    print('Standardized URL:', standardized_test_url)
    _, test_item = asyncio.run(naver.get_product_info(standardized_test_url))

    for key, value in test_item.items():
        print(key, '-', value)