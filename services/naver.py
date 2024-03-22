import re
import asyncio
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, BrowserContext
from typing import Union, Tuple
from services.base import AbstractService, BaseServiceItem, USER_AGENT
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
            'max_point': {'label': '최대 적립 포인트', 'type': str, 'value': ''},
            'availability': {'label': '재고', 'type': str, 'value': ''},
            'thumbnail': {'type': str, 'value': ''}
        }

        super().__init__(naver_dict, **kwargs)


class NaverService(AbstractService):
    SERVICE_DEFAULT_CONFIG = {
        'login': False,
        'id': '',
        'password': ''
    }
    SERVICE_NAME = 'naver'
    SERVICE_LABEL = '네이버'
    SERVICE_COLOR = 0x5ECC69
    SERVICE_ICON = get_favicon('https://www.naver.com/')
    SERVICE_USES_PLAYWRIGHT = True

    def __init__(self, cfg, chromium_path=None):
        self.LOGIN = cfg['login']
        self.NAVER_ID = cfg['id']
        self.NAVER_PW = cfg['password']
        self.chromium_path = chromium_path

        if not self.LOGIN:
            pprint("Warning: login is disabled. "
                   "Maximum points will be inaccurate and benefit price won't be available")
        pprint('naver service initialized.')

    async def standardize_url(self, url) -> Union[str, None]:
        if 'naver.me' in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    url = str(r.url)

        url = url.replace('m.', '')

        if 'brand.naver.com' in url:
            url = re.findall('https://brand.naver.com/[\S]*/products/[0-9]*', url)[0]
        elif 'smartstore.naver.com' in url:
            url = re.findall('https://smartstore.naver.com/[\S]*/products/[0-9]*', url)[0]
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
        await main_page.wait_for_load_state('networkidle')

        try:
            await main_page.locator('#new\.save').click(timeout=1000)
        except PlaywrightTimeoutError:
            try:
                await main_page.locator('#err_common > div').is_visible(timeout=100)
                raise ValueError('Login failed due to incorrect ID or password.')
            except PlaywrightTimeoutError:
                pass

        await main_page.wait_for_load_state('networkidle')

    async def fetch_items(self, url_list: list) -> dict:
        if url_list:
            async with async_playwright() as p:
                browser = await p.chromium.launch(executable_path=self.chromium_path, headless=HEADLESS, slow_mo=DELAY)
                context = await browser.new_context(
                    user_agent=USER_AGENT)
                context.set_default_timeout(10000)

                if self.LOGIN:
                    await self._login(context)

                results = await asyncio.gather(*[self.get_product_info(url, context) for url in url_list])

                await context.close()
                await browser.close()

            result_dict = {}

            for result in results:
                result_dict[result[0]] = result[1]

            return result_dict
        else:
            return {}

    async def get_product_info(self, url: str, context: BrowserContext = None) -> Tuple[str, NaverItem]:
        if context is None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(executable_path=self.chromium_path, headless=HEADLESS, slow_mo=DELAY)
                context = await browser.new_context(
                    user_agent=USER_AGENT)
                context.set_default_timeout(10000)

                if self.LOGIN:
                    await self._login(context)

                url, item = await self.get_product_info(url, context)
                await context.close()
                await browser.close()

            return url, item

        product_page = await context.new_page()
        await product_page.goto(url)

        item_name = await product_page.wait_for_selector(
            '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
            'div._3k440DUKzy > div._1eddO7u4UC > h3')
        item_name = await item_name.text_content()

        current_price = await product_page.wait_for_selector(
            '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
            'div._3k440DUKzy > div.WrkQhIlUY0 > div > strong > span._1LY7DqCnwR'
        )
        current_price = await current_price.text_content() + '원'

        thumbnail = await product_page.wait_for_selector(
            '#content > div > div._2-I30XS1lA > div._3rXou9cfw2 > div.bd_23RhM > div.bd_1uFKu > img'
        )
        thumbnail = await thumbnail.get_attribute('src')

        oos = '이 상품은 현재 구매하실 수 없는 상품입니다.' in await product_page.content()

        if oos:
            availability = '품절'
        else:
            availability = '재고 있음'

        if self.LOGIN:
            try:
                benefit_price = await product_page.wait_for_selector(
                    '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
                    'div._2a18RJADk5 > div._1UNQIwX1sN > div > strong._-2CCeRkfCX > span',
                    timeout=1000)
                benefit_price = await benefit_price.text_content() + '원'
            except PlaywrightTimeoutError:
                benefit_price = ''

            try:
                max_point = await product_page.wait_for_selector(
                    '#content > div > div._2-I30XS1lA > div._2QCa6wHHPy > fieldset > '
                    'div._2a18RJADk5 > div._3gd5biYh9U > div > div > span',
                )
                max_point = await max_point.text_content() + '원'
            except PlaywrightTimeoutError:
                benefit_price = ''
                max_point = ''
        else:
            benefit_price = ''
            max_point = ''

        item = NaverItem(
            name=item_name,
            price=current_price,
            benefit_price=benefit_price,
            max_point=max_point,
            availability=availability,
            thumbnail=thumbnail
        )

        return url, item


if __name__ == '__main__':
    use_login = True if input('Use login? (y/N): ').strip().lower() == 'y' else False
    naver = NaverService({
        'login': use_login,
        'id': input('Enter naver ID: ') if use_login else '',
        'password': input('Enter naver PW: ') if use_login else ''
    })
    print('Naver module test')
    test_url = input('Enter naver shopping URL: ')
    standardized_test_url = asyncio.run(naver.standardize_url(test_url))
    print('Standardized URL:', standardized_test_url)
    _, test_item = asyncio.run(naver.get_product_info(standardized_test_url))

    for key, value in test_item.items():
        print(key, '-', value)
