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
TARGET_USER = 000000000000000000  # 여기에 본인의 디스코드 유저 ID 입력
TEST_MODE = False  # 테스트 모드 True로 설정시 10초마다 가격 표시
INTERVAL = 60  # 가격을 확인할 주기

EMAIL = ''  # 쿠팡 이메일
PW = ''  # 쿠팡 비밀번호

POST_DATA = {'email': EMAIL,
             'password': PW,
             'rememberMe': 'false'}

if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):  # 파이썬 3.8 이상 & Windows 환경에서 실행하는 경우
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class CoupangPriceBot(commands.Bot):
    def __init__(self):
        super().__init__('!')
        self.init = True
        self.item_dict = {}
        self.add_commands()
        self.bg_task = self.loop.create_task(self.check_price())

    def add_commands(self):
        @self.command(name='items')
        async def items(ctx):
            await self.fetch_coupang()
            await ctx.send(f'찜 목록에 {str(len(self.item_dict))} 개의 상품이 있습니다.\n\n' +
                           '\n\n'.join([f'{value["item_name"]}: {value["price"]}\n{key}' for key, value in self.item_dict.items()]))

    async def fetch_coupang(self):
        header = {'User-Agent': USER_AGENT,
                  'Connection': 'keep-alive'}

        login_header = {'User-Agent': USER_AGENT,
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Host': 'login.coupang.com',
                        'Referer': 'https://login.coupang.com/login/login.pang',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'X-Requested-With': 'XMLHttpRequest'}

        try:
            async with aiohttp.ClientSession(headers=header) as session:
                print('Sending GET to login page...')
                await session.get('https://login.coupang.com/login/login.pang')

                print('Sending POST to loginProcess...')
                await session.post('https://login.coupang.com/login/loginProcess.pang', headers=login_header, data=POST_DATA)

                print('Sending GET to wish list page...')
                async with session.get('https://wish-web.coupang.com/wishInitView.pang') as r:
                    text = await r.read()
                    soup = BeautifulSoup(text, 'html.parser')

                    url_list = []
                    name_list = []
                    price_list = []
                    price_int_list = []

                    names = soup.find_all('a', class_='item-name')
                    for name in names:
                        url_list.append(f'https:{str(name.attrs["href"])}')
                        name_list.append(re.sub('<[^<>]*>', '', str(name)))

                    prices = soup.find_all('span', class_='item-price')
                    for price in prices:
                        price_str = re.sub('<[^<>]*>', '', str(price))
                        price_int = re.sub('[^0-9]', '', str(price))

                        if price_str != '원':
                            price_list.append(price_str)
                            price_int_list.append(price_int)

                    for i, url in enumerate(url_list):
                        self.item_dict[url] = {'item_name': name_list[i], 'price': price_list[i], 'price_int': price_int_list[i]}

        except Exception as e:
            await self.target.send(f'찜 목록을 불러오는 도중 오류가 발생했습니다: {e}')

    async def on_ready(self):
        print(f'Logged in as {self.user.name} | {self.user.id}')
        self.target = self.get_user(236122930709266432)

    async def check_price(self):
        await self.wait_until_ready()
        await asyncio.sleep(5)
        await self.fetch_coupang()

        await self.target.send(f'봇이 시작되었습니다. 찜 목록에 {str(len(self.item_dict))} 개의 상품이 있습니다.\n찜 목록을 확인하시려면 !items를 입력하세요.\n\n' +
                               '\n\n'.join([f'{value["item_name"]}: {value["price"]}\n{key}' for key, value in self.item_dict.items()]))

        if TEST_MODE is True:
            while True:
                print('Test mode enabled')
                last_dict = self.item_dict

                await self.fetch_coupang()

                for key, value in self.item_dict.items():
                    print(f'Sending {value["item_name"]} | {value["price"]} | {key}')
                    await self.target.send(f'{value["item_name"]} | {value["price"]} | {value["price_int"]} | {key}')

                await asyncio.sleep(10)
        else:
            while True:
                last_dict = self.item_dict

                await asyncio.sleep(INTERVAL)
                await self.fetch_coupang()

                for key, value in self.item_dict.items():
                    if value['price_int'] != last_dict[key]['price_int']:
                        await self.target.send(f'다음 상품의 가격이 변동되었습니다: {value["item_name"]}\n{last_dict[key]["price"]} -> {value["price"]}\n\n{key}')


bot = CoupangPriceBot()
bot.run(TOKEN)
