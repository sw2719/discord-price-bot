from discord.ext import commands
import asyncio
import aiohttp
import re
import sys
from bs4 import BeautifulSoup

print('Python version:', sys.version)

# 설정
TOKEN = ''  # 여기에 디스코드 봇 토큰 입력
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'  # 유저 에이전트
URL_LIST = ['']  # 여기에 쿠팡 URL 입력 ex) https://www.coupang.com/vp/products/332473915?itemId=1062243893
TARGET_USER = 000000000000000000  # 여기에 본인의 디스코드 유저 ID 입력
TEST_MODE = False  # 테스트 모드 True로 설정시 10초마다 가격 표시

if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):  # 파이썬 3.8 이상 & Windows 환경에서 실행하는 경우
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if not URL_LIST:
    raise Exception('No URL specified in URL_LIST')


class CoupangPriceBot(commands.Bot):
    def __init__(self):
        super().__init__('!')
        self.init = True
        self.item_dict = {}

        for url in URL_LIST:
            self.item_dict[url] = {}

        self.bg_task = self.loop.create_task(self.check_price())

    async def fetch_coupang(self, url):
        header = {'User-Agent': USER_AGENT,
                  'Connection': 'keep-alive'}
        async with aiohttp.ClientSession(headers=header) as session:
            try:
                async with session.get(url) as r:
                    text = await r.read()

                soup = BeautifulSoup(text, 'html.parser')
                price_match = soup.select('span.total-price > strong')

                price_output = [element for element in re.split('<[^<>]*>', str(price_match[0])) if element.strip()]
                current_price = ''.join(price_output)
                current_price_int = re.sub('[^0-9]', '', price_output[0])

                item_match = soup.find_all('h2', class_='prod-buy-header__title')
                item_name = re.sub('<[^<>]*>', '', str(item_match[0]))

                print(f'Got price of {url} ({item_name}): {current_price_int}')

                self.item_dict[url]['price'] = str(current_price)
                self.item_dict[url]['price_int'] = int(current_price_int)
                self.item_dict[url]['item_name'] = str(item_name)

            except Exception as e:
                await self.target.send(f'다음 상품의 가격을 불러오는 도중 오류가 발생했습니다: {url}\n{e}')

    async def on_ready(self):
        print(f'Logged in as {self.user.name} | {self.user.id}')
        self.target = self.get_user(236122930709266432)

    async def check_price(self):
        await self.wait_until_ready()

        tasks = [asyncio.create_task(self.fetch_coupang(url)) for url in URL_LIST]
        await asyncio.gather(*tasks)

        await self.target.send(f'봇이 시작되었습니다. {str(len(URL_LIST))}개의 상품을 감시 중입니다:\n' +
                               '\n'.join([f'{value["item_name"]}: {value["price"]}' for value in self.item_dict.values()]))

        if TEST_MODE is True:
            while True:
                try:
                    print('Test mode enabled')
                    last_dict = self.item_dict

                    await asyncio.gather(*[asyncio.create_task(self.fetch_coupang(url)) for url in URL_LIST])

                    for key, value in self.item_dict.items():
                        print(f'Sending {value["item_name"]} | {value["price"]} | {key}')
                        await self.target.send(f'{value["item_name"]} | {value["price"]} | {value["price_int"]} | {key}')

                    await asyncio.sleep(10)
                except Exception as e:
                    print(e)
                    await asyncio.sleep(10)
        else:
            while True:
                last_dict = self.item_dict
                await asyncio.gather(*tasks)

                for key, value in self.item_dict.items():
                    if value['price_int'] != last_dict[key]['price_int']:
                        await self.target.send(f'다음 상품의 가격이 변동되었습니다: {value["item_name"]}\n{last_dict[key]["price"]} -> {value["price"]}\n{key}')

                await asyncio.sleep(60)


bot = CoupangPriceBot()
bot.run(TOKEN)
