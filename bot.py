import sys
import asyncio
import json
import os
import logging
import traceback
import disnake as ds
from disnake.ext import commands
from typing import Union
from copy import deepcopy

from services.coupang import CoupangService
from services.danawa import DanawaService

# Add service class here to add new service
SERVICES = (CoupangService, DanawaService)


def reset_cfg():
    default = {"token": "",
               "user_id": "",
               "interval": 60,
               "test_mode": False
               }

    for service in SERVICES:
        if service.SERVICE_DEFAULT_CONFIG is not None:
            default[service.SERVICE_NAME] = service.SERVICE_DEFAULT_CONFIG

    with open('config.json', 'w') as new_file:
        new_file.write(json.dumps(default, indent=4))

    sys.exit(1)


class DiscordPriceBot(commands.Bot):
    COLOR_ERROR = 0xd1352a
    COLOR_SUCCESS = 0x39e360

    def __init__(self):
        intents = ds.Intents.default()
        intents.members = True
        super().__init__('.', intents=intents)
        self.init = True
        self.owner_id = int(cfg['user_id'])
        self.owner = None
        self.item_dict = {}

        try:
            with open('url.json', 'r') as f:
                self.url_dict = json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning('URL json file not found or invalid. Creating one')
            self.url_dict = {}

            with open('url.json', 'w') as f:
                json.dump(self.url_dict, f, indent=4)

        for service in SERVICES:
            if service.SERVICE_NAME not in self.url_dict:
                self.url_dict[service.SERVICE_NAME] = []

            self.item_dict[service.SERVICE_NAME] = {}

        self.services = {}

        for service in SERVICES:
            if service.SERVICE_DEFAULT_CONFIG is not None:
                self.services[service.SERVICE_NAME] = service(cfg[service.SERVICE_NAME])
            else:
                self.services[service.SERVICE_NAME] = service()

        self.command_busy = False

        asyncio.run(self.update_item_dict())
        self.add_bot_commands()
        self.bg_task = self.loop.create_task(self.check_price())

    def save_url_dict(self) -> None:
        with open('url.json', 'w') as f:
            json.dump(self.url_dict, f, indent=4)

    async def get_embed(self, title: Union[str, None], description: Union[str, None], color: int = 0x7289da,
                        author: str = '', icon: str = '', footer: str = '', url=None) -> ds.Embed:
        embed = ds.Embed(title=title, description=description, color=color, url=url)

        if footer:
            embed.set_footer(text=footer)

        if author:
            if icon:
                embed.set_author(name=author, icon_url=icon)
            else:
                embed.set_author(name=author)

        return embed

    async def update_item_dict(self) -> None:
        async def get(service):
            self.item_dict[service.SERVICE_NAME] = await service.fetch_items(self.url_dict[service.SERVICE_NAME])

        await asyncio.gather(*[get(service) for service in self.services.values()])

    async def on_command(self, ctx: commands.Context) -> None:
        self.command_busy = True

    async def on_command_completion(self, ctx: commands.Context) -> None:
        self.command_busy = False

    async def on_command_error(self, ctx: commands.Context, exception: commands.CommandError) -> None:
        self.command_busy = False
        title = '명령어 실패'

        tb = str(traceback.format_exception(type(exception), exception, exception.__traceback__))

        await ctx.send(embed=await self.get_embed(title, f'```{tb}```', color=self.COLOR_ERROR))

    async def check_command_eligibility(self, ctx: commands.Context) -> bool:
        title = '명령어 사용 불가'

        if ctx.author.id != self.owner_id:
            await ctx.send(embed=await self.get_embed(title, '권한이 없습니다.'))
            return False
        elif not isinstance(ctx.channel, ds.channel.DMChannel):
            await ctx.send(embed=await self.get_embed(title, 'DM에서만 명령어를 사용할 수 있습니다.'))
            return False
        elif self.command_busy:
            await ctx.send(embed=await self.get_embed(title, '이미 다른 명령어가 실행 중입니다.'))
            return False
        else:
            return True

    def add_bot_commands(self):
        self.remove_command('help')

        @self.command(name='help')
        async def help_(ctx):
            if not await self.check_command_eligibility(ctx):
                return

            embed = await self.get_embed('명령어 도움말', None)
            embed.add_field(name='```.add [상품 URL]```', value='봇에 해당 상품 URL을 추가합니다.', inline=False)
            embed.add_field(name='```.remove```', value='봇에서 상품을 제거합니다.', inline=False)
            embed.add_field(name='```.list```', value='추가된 상품 목록을 확인합니다.', inline=False)
            embed.add_field(name='```.info```', value='추가된 상품의 정보를 확인합니다.', inline=False)
            embed.add_field(name='```.help```', value='명령어 도움말을 확인합니다.', inline=False)

            await ctx.send(embed=embed)

        @self.command()
        async def add(ctx, input_url=None):
            if not await self.check_command_eligibility(ctx):
                return

            if input_url is None:
                def check(message):
                    return message.author.id == self.owner_id

                try:
                    await ctx.send(embed=await self.get_embed('상품 추가', '추가할 상품의 URL을 입력하세요.',
                                   footer="취소하려면 '취소'를 입력하세요."))
                    message = await self.wait_for('message', timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(embed=await self.get_embed('추가 취소됨', '입력 시간이 초과되었습니다. 다시 시도하세요.'))
                    return

                if message.content == '취소':
                    await ctx.send(embed=await self.get_embed('추가 취소됨', '추가를 취소했습니다.'))
                    return
                else:
                    input_url = message.content

            for service in self.services.values():
                if service.SERVICE_NAME in input_url:
                    break
            else:
                logger.warning('No substring of supported service name found in input URL: ' + input_url)
                await ctx.send(embed=await self.get_embed('추가 실패', '지원하지 않거나 올바르지 않은 URL입니다.', color=self.COLOR_ERROR))
                return

            if len(self.url_dict[service.SERVICE_NAME]) == 25:
                logger.warning('Maximum number of items reached for service: ' + service.SERVICE_NAME)
                await ctx.send(embed=await self.get_embed('추가 실패', '더 이상 해당 서비스의 상품을 추가할 수 없습니다.\n'
                                                                    '먼저 상품을 제거하세요.',
                                                          color=self.COLOR_ERROR))
                return

            standardized_url = await service.standardize_url(input_url)

            if standardized_url is None:
                logger.warning('Failed to standardize URL: ' + input_url)
                await ctx.send(embed=await self.get_embed('추가 실패', '지원하지 않거나 올바르지 않은 URL입니다.', color=self.COLOR_ERROR))
                return
            elif standardized_url in self.url_dict[service.SERVICE_NAME]:
                await ctx.send(embed=await self.get_embed('추가 실패', '이미 추가된 상품입니다.', color=self.COLOR_ERROR))
                return

            url, item_info = await service.get_product_info(standardized_url)
            self.url_dict[service.SERVICE_NAME].append(standardized_url)

            embed = await self.get_embed('상품 추가됨', '다음 상품을 추가했습니다.', color=self.COLOR_SUCCESS,
                                         author=service.SERVICE_LABEL, icon=service.SERVICE_ICON)

            for key, entry in item_info.items():
                value = entry['value']

                if key == 'thumbnail':
                    embed.set_thumbnail(url=value)
                    continue

                if not value:
                    continue

                try:
                    label = entry['label']

                    if entry['type'] is list:
                        value = ', '.join(value)
                    elif entry['type'] is dict:
                        string_list = []
                        for value_key, value_value in value.items():
                            string_list.append(f'{value_key}: {value_value}')

                        value = '\n'.join(string_list)

                    embed.add_field(name=label, value=value, inline=False)
                except KeyError:
                    if entry['type'] is dict:
                        for option_label, option in value.items():
                            embed.add_field(name=option_label, value=option, inline=False)

            embed.add_field(name='URL', value=url, inline=False)

            await ctx.send(embed=embed)
            await self.update_item_dict()
            self.save_url_dict()

        @self.command()
        async def remove(ctx):
            if not await self.check_command_eligibility(ctx):
                return

            embed = await self.get_embed('상품 제거', '제거할 상품이 해당되는 서비스의 번호를 입력하세요.',
                                         footer="취소하려면 '취소'를 입력하세요.")
            services_with_urls = []

            for i, (service_name, url_list) in enumerate(self.url_dict.items()):
                if url_list:
                    index = i + 1
                    services_with_urls.append(service_name)
                    embed.add_field(
                        name=f"{str(index)}: {self.services[service_name].SERVICE_LABEL}",
                        value=f"{len(url_list)}개 추가됨"
                    )

            service_count = len(services_with_urls)

            if service_count > 1:
                await ctx.send(embed=embed)

                def check_service(message):
                    try:
                        if message.content == '취소':
                            return True
                        else:
                            return message.author.id == self.owner_id and 1 <= int(message.content) <= service_count
                    except ValueError:
                        pass

                try:
                    message = await self.wait_for('message', timeout=30.0, check=check_service)
                except asyncio.TimeoutError:
                    await ctx.send(embed=await self.get_embed('제거 취소됨', '입력 시간이 초과되었습니다. 다시 시도하세요.'))
                    return

                if message.content == '취소':
                    await ctx.send(embed=await self.get_embed('제거 취소됨', '제거를 취소했습니다.'))
                    return
                else:
                    selected_service = services_with_urls[int(message.content) - 1]

            elif service_count == 1:
                selected_service = services_with_urls[0]

            else:
                await ctx.send(embed=await self.get_embed('제거 취소됨', '추가된 상품이 없습니다.'))
                return

            embed = await self.get_embed('상품 제거', "제거할 상품의 번호를 입력하세요.",
                                         footer="취소하려면 '취소'를 입력하세요.",
                                         author=self.services[selected_service].SERVICE_LABEL,
                                         icon=self.services[selected_service].SERVICE_ICON)

            for i, url in enumerate(self.url_dict[selected_service]):
                item = self.item_dict[selected_service][url]

                try:
                    options = ', '.join(item['option'])
                except KeyError:
                    options = ''

                embed.add_field(name=f"{i + 1}: {item['name']}",
                                value=options, inline=False)

            def check_item(message):
                nonlocal ctx

                try:
                    if message.content == '취소':
                        return True
                    else:
                        return message.author.id == self.owner_id and \
                            1 <= int(message.content) <= len(self.url_dict[selected_service])
                except ValueError:
                    pass

            await ctx.send(embed=embed)

            try:
                message = await self.wait_for('message', timeout=30.0, check=check_item)
            except asyncio.TimeoutError:
                await ctx.send(embed=await self.get_embed('제거 취소됨', '입력 시간이 초과되었습니다. 다시 시도하세요.'))
                return

            if message.content == '취소':
                await ctx.send(embed=await self.get_embed('제거 취소됨', '제거를 취소했습니다.'))
                return
            else:
                remove_index = int(message.content) - 1
                remove_url = self.url_dict[selected_service][remove_index]
                removed_item = self.item_dict[selected_service][remove_url]

                del self.item_dict[selected_service][remove_url]
                del self.url_dict[selected_service][remove_index]
                self.save_url_dict()

                embed = await self.get_embed('상품 제거됨', '다음 상품을 제거했습니다.', color=self.COLOR_SUCCESS,
                                             author=self.services[selected_service].SERVICE_LABEL,
                                             icon=self.services[selected_service].SERVICE_ICON)

                embed.add_field(name='상품명', value=removed_item['name'], inline=False)

                if 'option' in removed_item.keys():
                    for option_label, option in removed_item['option'].items():
                        embed.add_field(name=option_label, value=option, inline=False)

                embed.add_field(name='URL', value=remove_url, inline=False)

                await ctx.send(embed=embed)
                await self.update_item_dict()
                return

        @self.command()
        async def info(ctx):
            if not await self.check_command_eligibility(ctx):
                return

            embed = await self.get_embed('상품 정보', '정보를 확인할 상품이 해당되는 서비스의 번호를 입력하세요.',
                                         footer="취소하려면 '취소'를 입력하세요.")
            services_with_urls = []

            for i, (service_name, url_list) in enumerate(self.url_dict.items()):
                if url_list:
                    index = i + 1
                    services_with_urls.append(service_name)
                    embed.add_field(
                        name=f"{str(index)}: {self.services[service_name].SERVICE_LABEL}",
                        value=f"{len(url_list)}개 추가됨"
                    )

            service_count = len(services_with_urls)

            if service_count > 1:
                await ctx.send(embed=embed)

                def check_service(message):
                    try:
                        if message.content == '취소':
                            return True
                        else:
                            return message.author.id == self.owner_id and 1 <= int(message.content) <= service_count
                    except ValueError:
                        pass

                try:
                    message = await self.wait_for('message', timeout=30.0, check=check_service)
                except asyncio.TimeoutError:
                    await ctx.send(embed=await self.get_embed('정보 확인 취소됨', '입력 시간이 초과되었습니다. 다시 시도하세요.'))
                    return

                if message.content == '취소':
                    await ctx.send(embed=await self.get_embed('정보 확인 취소됨', '정보 확인을 취소했습니다.'))
                    return
                else:
                    selected_service = services_with_urls[int(message.content) - 1]

            elif service_count == 1:
                selected_service = services_with_urls[0]

            else:
                await ctx.send(embed=await self.get_embed('정보 확인 취소됨', '추가된 상품이 없습니다.'))
                return

            embed = await self.get_embed('상품 정보', "정보를 확인할 상품의 번호를 입력하세요.",
                                         footer="취소하려면 '취소'를 입력하세요.",
                                         author=self.services[selected_service].SERVICE_LABEL,
                                         icon=self.services[selected_service].SERVICE_ICON)

            for i, url in enumerate(self.url_dict[selected_service]):
                item = self.item_dict[selected_service][url]

                try:
                    options = ', '.join(item['option'])
                except KeyError:
                    options = ''

                embed.add_field(name=f"{i + 1}: {item['name']}",
                                value=options, inline=False)

            def check_item(message):
                nonlocal ctx

                try:
                    if message.content == '취소':
                        return True
                    else:
                        return message.author.id == self.owner_id and \
                            1 <= int(message.content) <= len(self.url_dict[selected_service])
                except ValueError:
                    pass

            await ctx.send(embed=embed)

            try:
                message = await self.wait_for('message', timeout=30.0, check=check_item)
            except asyncio.TimeoutError:
                await ctx.send(embed=await self.get_embed('정보 확인 취소됨', '입력 시간이 초과되었습니다. 다시 시도하세요.'))
                return

            if message.content == '취소':
                await ctx.send(embed=await self.get_embed('정보 확인 취소됨', '정보 확인을 취소했습니다.'))
                return
            else:
                service = self.services[selected_service]
                selected_index = int(message.content) - 1
                selected_url = self.url_dict[selected_service][selected_index]
                selected_item = self.item_dict[selected_service][selected_url]

                embed = await self.get_embed('상품 정보', None, color=service.SERVICE_COLOR,
                                             author=service.SERVICE_LABEL, icon=service.SERVICE_ICON)

                for key, entry in selected_item.items():
                    value = entry['value']

                    if key == 'thumbnail':
                        embed.set_thumbnail(url=value)
                        continue

                    if not value:
                        continue

                    try:
                        label = entry['label']

                        if entry['type'] is list:
                            value = ', '.join(value)
                        elif entry['type'] is dict:
                            string_list = []
                            for value_key, value_value in value.items():
                                string_list.append(f'{value_key}: {value_value}')

                            value = '\n'.join(string_list)

                        embed.add_field(name=label, value=value, inline=False)
                    except KeyError:
                        if entry['type'] is dict:
                            for option_label, option in value.items():
                                embed.add_field(name=option_label, value=option, inline=False)

                embed.add_field(name='URL', value=selected_url, inline=False)

                await ctx.send(embed=embed)
                return

        @self.command(name='list')
        async def list_(ctx):
            if not await self.check_command_eligibility(ctx):
                return

            embeds = []

            for service_name, url_list in self.url_dict.items():
                if url_list:
                    embed = await self.get_embed(None, None, author=self.services[service_name].SERVICE_LABEL,
                                                 icon=self.services[service_name].SERVICE_ICON)

                    for url in url_list:
                        item = self.item_dict[service_name][url]

                        options = []
                        try:
                            if item['option']:
                                for i, (option_name, option) in enumerate(item['option'].items()):
                                    options.append(f"{option_name}: {option}")

                                options_string = '\n' + '\n'.join(options)
                            else:
                                options_string = ''
                        except KeyError:
                            options_string = ''

                        embed.add_field(
                            name=item['name'],
                            value=f"{item['price']}{options_string}",
                            inline=False
                        )

                    embeds.append(embed)

            if embeds:
                await ctx.send(embeds=embeds)
            else:
                await ctx.send(embed=await self.get_embed('상품 목록', '추가된 상품이 없습니다.'))

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} | {self.user.id}')
        await self.wait_until_ready()
        logger.info('Target user ID is', self.owner_id)
        self.owner = await self.get_or_fetch_user(self.owner_id)

        if self.init:
            items_count = 0
            for url_list in self.url_dict.values():
                items_count += len(url_list)

            if items_count:
                await self.owner.send(embed=await self.get_embed(
                    "봇 시작됨", "명령어 목록을 보려면 '.help'를 입력하세요.\n\n" +
                    f'{items_count} 개의 상품을 확인 중입니다.'))
            else:
                await self.owner.send(embed=await self.get_embed(
                    "봇 시작됨", "명령어 목록을 보려면 '.help'를 입력하세요.\n\n" +
                    f'추가된 상품이 없습니다.'))

            self.init = False

    async def check_price(self):
        await asyncio.sleep(5)
        if cfg['test_mode'] is True:
            logger.info('Test mode enabled')
            while True:
                self.item_dict = {}
                await self.update_item_dict()
                for service_name, service_item_dict in self.item_dict.items():
                    for url, item in service_item_dict.items():
                        logger.info(f'{item["name"]} | {item["price"]} | {url}')

                await asyncio.sleep(10)

        else:
            while True:
                logger.info('Starting price check cycle...')
                try:
                    last_dict = self.item_dict
                    await self.update_item_dict()
                    current_dict = deepcopy(self.item_dict)

                    for service_name, service_item_dict in current_dict.items():
                        try:
                            for url, item in service_item_dict.items():
                                last_item = last_dict[service_name][url]

                                if item != last_item:
                                    embed = await self.get_embed(
                                         '상품 정보 변경됨', '다음 상품의 정보가 변경되었습니다.',
                                         author=self.services[service_name].SERVICE_LABEL,
                                         icon=self.services[service_name].SERVICE_ICON,
                                         color=self.services[service_name].SERVICE_COLOR
                                    )

                                    for key, entry in item.items():
                                        item_value = entry['value']
                                        last_value = last_item[key]

                                        item_value_string = item_value
                                        last_value_string = last_value

                                        if key == 'thumbnail':
                                            embed.set_thumbnail(url=item_value)
                                            continue

                                        try:
                                            label = entry['label']

                                            if entry['type'] is list:
                                                item_value_string = ', '.join(item_value)
                                                last_value_string = ', '.join(last_value)
                                            elif entry['type'] is dict:
                                                string_list = []
                                                last_string_list = []
                                                for value_key, value_value in item_value.items():
                                                    string_list.append(f'{value_key}: {value_value}')

                                                for last_value_key, last_value_value in last_value.items():
                                                    last_string_list.append(f'{last_value_key}: {last_value_value}')

                                                item_value_string = ' / '.join(string_list)
                                                last_value_string = ' / '.join(last_string_list)

                                            if item_value != last_item[key]:
                                                if not item_value:
                                                    item_value_string = '없음'
                                                if not last_value:
                                                    last_value_string = '없음'

                                                embed.add_field(
                                                    name=label,
                                                    value=f'{last_value_string} -> {item_value_string}',
                                                    inline=False)
                                            else:
                                                if item_value:
                                                    embed.add_field(name=label, value=item_value_string, inline=False)

                                        except KeyError:
                                            if entry['type'] is dict:
                                                for option_label, option in item_value.items():
                                                    if option != last_value[option_label]:
                                                        embed.add_field(
                                                            name=option_label,
                                                            value=f'{last_value[option_label]} -> {option}',
                                                            inline=False
                                                        )
                                                    else:
                                                        embed.add_field(name=option_label, value=option, inline=False)

                                    embed.add_field(name='URL', value=url, inline=False)
                                    await self.owner.send(embed=embed)

                        except KeyError:  # New items
                            pass

                    logger.info('Price check cycle ended.')
                    await asyncio.sleep(cfg['interval'])

                except Exception as e:
                    logger.error(f'Price check failed with exception {e}')
                    traceback.print_tb(e.__traceback__)
                    await asyncio.sleep(5)


if __name__ == '__main__':
    logger = logging.getLogger('bot')
    logger.setLevel(logging.INFO)

    print('Python version:', sys.version)

    # 파이썬 3.8 이상 & Windows 환경에서 실행하는 경우
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if not os.path.isfile('config.json'):
        logger.warning('config.json not found. Creating new config file. Please fill in the required information.')
        reset_cfg()
    else:
        try:
            with open('config.json', 'r') as f:
                cfg = json.loads(f.read())

            del f

        except KeyError:
            reset_cfg()

    bot = DiscordPriceBot()
    bot.run(cfg['token'])
