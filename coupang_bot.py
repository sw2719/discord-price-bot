import sys
import asyncio
import re
import logging
import traceback
import aiohttp
from discord.ext import commands
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.WARNING)

print('Python version:', sys.version)

if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):  # 파이썬 3.8 이상 & Windows 환경에서 실행하는 경우
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 설정
TARGET_USER_ID = 0  # 자신의 디스코드 유저 ID 입력
TOKEN = ''  # 디스코드 봇 토큰 입력
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'  # 유저 에이전트
TEST_MODE = False
INTERVAL = 45  # 가격을 확인할 주기 (초)


class CoupangPriceBot(commands.Bot):
    def __init__(self):
        super().__init__('.')
        self.item_dict = {}
        self.header = {'User-Agent': USER_AGENT, 'Connection': 'keep-alive'}

        try:
            with open('url.txt', 'r') as txt:
                self.url_list = txt.read().splitlines()

            to_remove = []

            for url in self.url_list:
                re_output = re.match('https://www.coupang.com/vp/products/[0-9]+', url)

                if not re_output:
                    to_remove.append(url)

                elif url != re_output.group():
                    to_remove.append(url)
                    self.url_list.append(re_output.group())

            if to_remove:
                for url_to_remove in to_remove:
                    self.url_list.remove(url_to_remove)

                print(f'Deleted {len(to_remove)} bad URLs.')
                self.save_url_list()

        except FileNotFoundError:
            print('URL file not found. Creating one!')
            open('url.txt', 'w').close()
            self.url_list = []

        self.add_bot_commands()
        self.bg_task = self.loop.create_task(self.check_price())

    def save_url_list(self):
        with open('url.txt', 'w') as txt:
            txt.write('\n'.join(self.url_list))

    def add_bot_commands(self):
        @self.command()
        async def commands(ctx):
            if ctx.author.id == self.owner_id:
                await ctx.send('```명령어 도움말\n\n.add [상품 URL]\n봇에 해당 상품 URL을 추가합니다.\n\n.remove - 봇에서 상품을 제거합니다.\n\n.list - 추가된 상품 목록을 확인합니다.```')

        @self.command()
        async def add(ctx, url=None):
            if ctx.author.id != self.owner_id:
                return

            if url is None:
                def check(message):
                    return message.author.id == self.owner_id

                try:
                    await ctx.send('추가할 상품의 URL을 입력하세요.')
                    message = await self.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send('시간이 초과되었습니다. 다시 시도하세요.')
                    return

                if message.content == '취소':
                    await ctx.send('삭제를 취소했습니다.')
                    return
                else:
                    url = message.content

            result = await self.fetch_coupang(url, return_value=True)

            if result:
                price, _, item_name = result
            else:
                ctx.send('오류: 올바르지 않은 URL이거나 현재 판매하지 않는 상품입니다.')
                return

            clean_url = url.split('?')[0]

            if clean_url not in self.url_list:
                self.url_list.append(clean_url)
                self.save_url_list()

                await ctx.send(f'{item_name} 상품이 추가되었습니다.\n현재 {price}')
            else:
                await ctx.send('알림: 이미 추가된 URL입니다.')

            return

        @self.command()
        async def remove(ctx):
            if ctx.author.id != self.owner_id:
                return
            elif not self.url_list:
                await ctx.send('추가된 상품이 없습니다.')
                return

            tasks = [self.fetch_coupang(url) for url in self.url_list]
            await asyncio.gather(*tasks)

            message_to_send = ["삭제할 상품의 번호를 입력하세요. (예시: 1)\n취소하려면 '취소'라고 입력하세요.\n"]

            for i, url in enumerate(self.url_list):
                index = i + 1
                message_to_send.append(f"{str(index)}: {self.item_dict[url]['item_name']}")

            await ctx.send('\n'.join(message_to_send))

            def check(message):
                try:
                    if message.content == '취소':
                        return True
                    else:
                        return message.author.id == self.owner_id and 1 <= int(message.content) <= len(self.url_list)
                except ValueError:
                    pass

            try:
                message = await self.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send('시간이 초과되었습니다. 다시 시도하세요.')
                return

            if message.content == '취소':
                await ctx.send('삭제를 취소했습니다.')
                return

            remove_index = int(message.content) - 1
            removed_item = self.item_dict[self.url_list[remove_index]]['item_name']

            del self.url_list[remove_index]
            self.save_url_list()

            await ctx.send(f'{removed_item}을(를) 삭제했습니다.')
            return

        @self.command(name='list')
        async def list_(ctx):
            if self.url_list:
                await asyncio.gather(*[self.fetch_coupang(url) for url in self.url_list])
                await ctx.send(f'{str(len(self.url_list))} 개의 상품을 감시 중입니다.\n\n' +
                               '\n'.join([f'{value["item_name"]} - {value["price"]}' for value in self.item_dict.values()]))
            else:
                await ctx.send('추가된 상품이 없습니다.')

    async def fetch_coupang(self, url, return_value=False):
        try:
            async with aiohttp.ClientSession(headers=self.header) as session:
                async with session.get(url) as r:
                    soup = BeautifulSoup(await r.read(), 'html.parser')

            price_match = soup.select('span.total-price > strong')
            item_match = soup.find_all('h2', class_='prod-buy-header__title')
            item_name = re.sub('<[^<>]*>', '', str(item_match[0]))

            if soup.find_all('div', class_='oos-label') or not price_match:
                current_price = '품절'
                current_price_int = 0

            else:
                price_output = [element for element in re.split('<[^<>]*>', str(price_match[0])) if element.strip()]

                current_price = ''.join(price_output)
                current_price_int = re.sub('[^0-9]', '', price_output[0])

            print(f'Got price of {url} ({item_name}): {current_price_int}')

            if str(current_price) == '품절':
                current_price = '*품절*'

            if return_value and str(item_name):
                return str(current_price), int(current_price_int), str(item_name)
            elif str(item_name):
                self.item_dict[url] = {}
                self.item_dict[url]['price'] = str(current_price)
                self.item_dict[url]['price_int'] = int(current_price_int)
                self.item_dict[url]['item_name'] = str(item_name)

        except Exception as e:
            print(traceback.format_exc())

            if return_value:
                return False
            else:
                await self.target.send(f'다음 상품의 가격을 불러오는 도중 오류가 발생했습니다: {url}\n{e}')

    async def on_ready(self):
        print(f'Logged in as {self.user.name} | {self.user.id}')
        self.owner_id = TARGET_USER_ID
        self.target = self.get_user(self.owner_id)

        await asyncio.gather(*[self.fetch_coupang(url) for url in self.url_list])
        if self.url_list:
            await self.target.send("봇이 시작되었습니다. 명령어 목록을 보려면 '.commands'를 입력하세요.\n" +
                                   f'{str(len(self.url_list))} 개의 상품을 감시 중입니다.\n\n' +
                                   '\n'.join([f'{value["item_name"]} - {value["price"]}' for value in self.item_dict.values()]))
        else:
            await self.target.send("봇이 시작되었습니다. 명령어 목록을 보려면 '.commands'를 입력하세요.\n\n" +
                                   '추가된 상품이 없습니다.')

    async def check_price(self):
        await asyncio.sleep(5)
        if TEST_MODE is True:
            while not self.is_closed():
                print('Test mode enabled')
                last_dict = self.item_dict
                self.item_dict = {}
                await asyncio.gather(*[self.fetch_coupang(url) for url in self.url_list])

                for key, value in self.item_dict.items():
                    print(f'Sending {value["item_name"]} | {value["price"]} | {key}')
                    await self.target.send(f'{value["item_name"]} | {value["price"]} | {value["price_int"]} | {key}')

                await asyncio.sleep(10)

        else:
            while not self.is_closed():
                print('Starting price check...')
                try:
                    last_dict = self.item_dict
                    self.item_dict = {}
                    await asyncio.gather(*[self.fetch_coupang(url) for url in self.url_list])

                    for key, value in self.item_dict.items():
                        try:
                            if value['price_int'] != last_dict[key]['price_int']:
                                await self.target.send(f'다음 상품의 상태가 변경되었습니다: {value["item_name"]}\n\n{last_dict[key]["price"]} -> {value["price"]}\n{key}')
                        except KeyError:
                            pass

                    print('Price check ended successfully.')
                    await asyncio.sleep(INTERVAL)

                except Exception as e:
                    print(f'Price check failed with exception {e}')
                    await asyncio.sleep(5)


bot = CoupangPriceBot()
bot.run(TOKEN)
