import re
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, BrowserContext
from typing import Union, Tuple
from services.base import AbstractService, BaseServiceItem, USER_AGENT
from util.favicon import get_favicon

# Debug settings
HEADLESS = True
DELAY = 0


def pprint(*args, **kwargs):
    print('[11st]', *args, **kwargs)


class EleventhStreetItem(BaseServiceItem):
    def __init__(self, **kwargs):
        naver_dict = {
            'name': {'label': '상품명', 'type': str, 'value': ''},
            'price': {'label': '가격', 'type': str, 'value': ''},
            'coupon': {'label': '쿠폰', 'type': str, 'value': ''},
            'delivery': {'label': '배송비', 'type': str, 'value': ''},
            'agency_fee': {'label': '예상 통관대행료', 'type': str, 'value': ''},
            'thumbnail': {'type': str, 'value': ''}
        }

        super().__init__(naver_dict, **kwargs)


class EleventhStreetService(AbstractService):
    SERVICE_DEFAULT_CONFIG = None
    SERVICE_NAME = '11st'
    SERVICE_LABEL = '11번가'
    SERVICE_COLOR = 0xea3a40
    SERVICE_ICON = get_favicon('https://www.11st.co.kr/')

    def __init__(self):
        pprint('11st service initialized.')

    async def standardize_url(self, url) -> Union[str, None]:
        if 'share?gsreferrer=' in url:
            return str(re.sub('/share\?gsreferrer=.*', '', url))

        if 'https://www.11st.co.kr/products' in url:
            return url.split('?')[0]
        elif 'http://m.11st.co.kr/products/m' in url:
            return url.split('?')[0]

        return None

    async def fetch_items(self, url_list: list) -> dict:
        if url_list:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=HEADLESS, slow_mo=DELAY)
                context = await browser.new_context(
                    user_agent=USER_AGENT)
                context.set_default_timeout(10000)

                results = await asyncio.gather(*[self.get_product_info(url, context) for url in url_list])

                await context.close()
                await browser.close()

            result_dict = {}

            for result in results:
                result_dict[result[0]] = result[1]

            return result_dict
        else:
            return {}

    async def get_product_info(self, url: str, context: BrowserContext = None) -> Tuple[str, EleventhStreetItem]:
        if context is None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=HEADLESS, slow_mo=DELAY)
                context = await browser.new_context(
                    user_agent=USER_AGENT)
                context.set_default_timeout(10000)

                url, item = await self.get_product_info(url, context)
                await context.close()
                await browser.close()

            return url, item

        product_page = await context.new_page()
        await product_page.goto(url)

        item_name = await product_page.wait_for_selector('h1.title')
        item_name = await item_name.text_content()
        item_name = item_name.strip()

        price = await product_page.wait_for_selector('dl.price > dd > strong')
        price = await price.text_content()
        price = price.strip()

        try:
            await product_page.wait_for_selector('dl > div.coupon', timeout=100)
            coupon = '있음'
        except PlaywrightTimeoutError:
            coupon = '없음'

        try:
            agency_fee = await product_page.wait_for_selector('div.c_product_agency_fee > div > dl > dd', timeout=100)
            agency_fee = await agency_fee.text_content()

            if '없음' in agency_fee:
                agency_fee = '없음'
            else:
                agency_fee = agency_fee.split(' ')[0]
                agency_fee = agency_fee.strip()
        except PlaywrightTimeoutError:
            agency_fee = '해외직구 상품 아님'

        try:
            delivery = await product_page.wait_for_selector('div.delivery', timeout=100)
        except PlaywrightTimeoutError:
            delivery = await product_page.wait_for_selector('div.delivery_abroad', timeout=100)

        delivery = await delivery.text_content()

        if '무료배송' in delivery:
            delivery = '무료배송'
        else:
            delivery = '유료배송'

        try:
            thumbnail = await product_page.wait_for_selector('#productImg > div > img', timeout=100)
        except PlaywrightTimeoutError:
            thumbnail = await product_page.wait_for_selector(
                'div.l_product_side_view > div.c_product_view_img > div.img_full.img_full_height > img'
            )

        thumbnail = await thumbnail.get_attribute('src')

        item = EleventhStreetItem(
            name=item_name,
            price=price,
            coupon=coupon,
            delivery=delivery,
            agency_fee=agency_fee,
            thumbnail=thumbnail
        )

        return url, item


if __name__ == '__main__':
    eleventhst = EleventhStreetService()
    print('11st module test')
    test_url = input('Enter 11st item URL: ')
    standardized_test_url = asyncio.run(eleventhst.standardize_url(test_url))
    print('Standardized URL:', standardized_test_url)
    _, test_item = asyncio.run(eleventhst.get_product_info(standardized_test_url))

    for key, value in test_item.items():
        print(key, '-', value)
