import sys
import asyncio
import json
import os
import logging
import traceback
from copy import deepcopy

import aiohttp
import discord as ds  # noqa
from discord.ext.commands import NotOwner  # noqa

from util.embed_factory import get_embed
from views.menu import MenuView
from services.coupang import CoupangService
from services.danawa import DanawaService
from services.naver import NaverService
from services.eleventhst import EleventhStreetService
from services.univstore import UnivStoreService

# Add service class here to add new service
SERVICES = (CoupangService, DanawaService, NaverService, EleventhStreetService, UnivStoreService)


def reset_cfg():
    default = {"token": "",
               "user_id": "",
               "interval": 60,
               "test_mode": False,
               "chromium_executable_override": ""
               }

    for service in SERVICES:
        if service.SERVICE_DEFAULT_CONFIG is not None:
            default[service.SERVICE_NAME] = service.SERVICE_DEFAULT_CONFIG

    with open('config.json', 'w') as new_file:
        new_file.write(json.dumps(default, indent=4))

    sys.exit(1)


class DiscordPriceBot(ds.Bot):
    COLOR_ERROR = 0xd1352a
    COLOR_SUCCESS = 0x39e360

    def __init__(self):
        self.initialized = False
        self.owner_id = int(cfg['user_id'])
        self.target = None
        self.interaction = False

        intents = ds.Intents.default()
        intents.members = True  # noqa
        super().__init__(intents=intents, owner_id=self.owner_id)

        self.item_dict = {}

        try:
            with open('url.json', 'r') as f:
                self.url_dict = json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            print('URL json file not found or invalid. Creating one')
            self.url_dict = {}

            with open('url.json', 'w') as f:
                json.dump(self.url_dict, f, indent=4)

        for service in SERVICES:
            if service.SERVICE_NAME not in self.url_dict:
                self.url_dict[service.SERVICE_NAME] = []

            self.item_dict[service.SERVICE_NAME] = {}

        self.services = {}

        config_updated = False

        for service in SERVICES:
            if service.SERVICE_DEFAULT_CONFIG is not None:
                print('Testing config for', service.SERVICE_NAME)

                try:
                    service_cfg = cfg[service.SERVICE_NAME]
                except KeyError:
                    print(f'Config for {service.SERVICE_NAME} not found. Creating one')
                    cfg[service.SERVICE_NAME] = deepcopy(service.SERVICE_DEFAULT_CONFIG)
                    config_updated = True
                    continue

                for key in service.SERVICE_DEFAULT_CONFIG:
                    if key not in service_cfg:
                        print(f'Config for {service.SERVICE_NAME} is missing key {key}. Resetting to default...')
                        cfg[service.SERVICE_NAME] = deepcopy(service.SERVICE_DEFAULT_CONFIG)
                        config_updated = True
                        break
            else:
                print(f'No config required for {service.SERVICE_NAME}')

        if config_updated:
            with open('config.json', 'w') as f:
                json.dump(cfg, f, indent=4)

            print('Updated config file. Please review and edit settings as needed.')
            sys.exit(1)

        if cfg['chromium_executable_override'] != "" and os.path.exists(cfg['chromium_executable_override']):
            chromium_path = cfg['chromium_executable_override']
            print('Using chromium path:', chromium_path)
        else:
            chromium_path = None

        for service in SERVICES:
            print('Initializing service:', service.SERVICE_NAME)
            if service.SERVICE_USES_PLAYWRIGHT and service.SERVICE_DEFAULT_CONFIG is not None:
                self.services[service.SERVICE_NAME] = service(cfg[service.SERVICE_NAME], chromium_path)
            elif service.SERVICE_USES_PLAYWRIGHT:
                self.services[service.SERVICE_NAME] = service(chromium_path)
            elif service.SERVICE_DEFAULT_CONFIG is not None:
                self.services[service.SERVICE_NAME] = service(cfg[service.SERVICE_NAME])
            else:
                self.services[service.SERVICE_NAME] = service()

        self.command_busy = False
        self.message_with_view_id = None

        print('Initializing item dict...')
        asyncio.run(self.update_item_dict())
        self.bg_task = self.loop.create_task(self.check_price())

    def save_url_dict(self) -> None:
        with open('url.json', 'w') as f:
            json.dump(self.url_dict, f, indent=4)

    async def update_item_dict(self) -> None:
        async def get(service):
            if self.url_dict[service.SERVICE_NAME]:
                self.item_dict[service.SERVICE_NAME] = await service.fetch_items(self.url_dict[service.SERVICE_NAME])
            else:
                self.item_dict[service.SERVICE_NAME] = {}

        await asyncio.gather(*[get(service) for service in self.services.values()])

    def get_menu_view(self):
        return MenuView(self.services, self.item_dict, self.add, self.list_,
                        self.info, self.delete, self.interaction_start, self.select_cancel)

    async def interaction_start(self):
        self.interaction = True

    async def select_cancel(self, interaction: ds.Interaction):
        await interaction.edit_original_response(content=None, embed=None, view=self.get_menu_view())
        self.interaction = False

    async def add(self, interaction: ds.Interaction, input_url: str):
        print('Trying to add URL:', input_url)

        context_text = '상품을 추가하는 중입니다...'
        await interaction.response.edit_message(embed=get_embed('상품 추가', context_text), view=None)

        async def update_context_message(text):
            nonlocal context_text
            nonlocal interaction
            context_text += '\n' + text
            await interaction.edit_original_response(embed=get_embed('상품 추가', context_text))

        for service in self.services.values():
            if service.SERVICE_NAME in input_url:
                print('Found matching service:', service.SERVICE_NAME)
                await update_context_message('URL에 해당하는 서비스를 찾았습니다: ' + service.SERVICE_LABEL)
                break
        else:
            print('No substring of supported service name found in input URL: ' + input_url)
            response_with_view = await interaction.edit_original_response(
                embed=get_embed('추가 실패', '지원하지 않거나 올바르지 않은 URL입니다.', color=self.COLOR_ERROR),
                view=self.get_menu_view()
            )
            self.message_with_view_id = response_with_view.id
            await interaction.edit_original_response(view=self.get_menu_view())
            self.interaction = False
            return

        if len(self.url_dict[service.SERVICE_NAME]) == 25:
            print('Maximum number of items reached for service: ' + service.SERVICE_NAME)
            response_with_view = await interaction.edit_original_response(
                embed=get_embed(
                    '추가 실패', '더 이상 해당 서비스의 상품을 추가할 수 없습니다.\n'
                    '먼저 상품을 제거하세요.',
                    color=self.COLOR_ERROR
                ),
                view=self.get_menu_view()
            )
            self.message_with_view_id = response_with_view.id
            self.interaction = False
            return

        standardized_url = await service.standardize_url(input_url)
        print('Standardized URL:', standardized_url)

        if standardized_url is None:
            print('Failed to standardize URL: ' + input_url)
            response_with_view = await interaction.edit_original_response(
                embed=get_embed('추가 실패', '지원하지 않거나 올바르지 않은 URL입니다.', color=self.COLOR_ERROR),
                view=self.get_menu_view()
            )
            self.message_with_view_id = response_with_view.id
            self.interaction = False
            return
        elif standardized_url in self.url_dict[service.SERVICE_NAME]:
            print('URL already added: ' + standardized_url)
            response_with_view = await interaction.edit_original_response(
                embed=get_embed('추가 실패', '이미 추가된 URL입니다.', color=self.COLOR_ERROR),
                view=self.get_menu_view()
            )
            self.message_with_view_id = response_with_view.id
            self.interaction = False
            return
        else:
            await update_context_message('일반화된 URL: ' + standardized_url)

        print('Fetching item info...')
        await update_context_message('상품 정보를 가져오는 중...')

        try:
            url, item_info = await service.get_product_info(standardized_url)
        except aiohttp.client.ClientError as e:
            print(e, 'while fetching item status of URL: ' + input_url)
            response_with_view = await interaction.edit_original_response(
                embed=get_embed('추가 실패', '상품 정보를 가져오는 데 실패했습니다.', color=self.COLOR_ERROR),
                view=self.get_menu_view()
            )
            self.message_with_view_id = response_with_view.id
            self.interaction = False
            return

        self.url_dict[service.SERVICE_NAME].append(standardized_url)

        embed = get_embed('상품 추가됨', '다음 상품을 추가했습니다.',
                          color=service.SERVICE_COLOR,
                          author=service.SERVICE_LABEL,
                          icon=service.SERVICE_ICON)

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

        response_with_view = await interaction.edit_original_response(embed=embed, view=self.get_menu_view())
        self.interaction = False
        self.message_with_view_id = response_with_view.id
        self.item_dict[service.SERVICE_NAME][url] = item_info
        self.save_url_dict()

    async def delete(self, interaction: ds.Interaction, service_name: str, delete_url_list: list):
        embed = get_embed('상품 제거됨', '다음 상품을 제거했습니다.',
                          color=self.services[service_name].SERVICE_COLOR,
                          author=self.services[service_name].SERVICE_LABEL,
                          icon=self.services[service_name].SERVICE_ICON)

        for url in delete_url_list:
            deleted_item = self.item_dict[service_name][url]
            del self.item_dict[service_name][url]

            self.url_dict[service_name].remove(url)

            options = []
            try:
                if deleted_item['option']:
                    for option_name, option in deleted_item['option'].items():
                        options.append(f"{option_name}: {option}")

                    options_string = '\n'.join(options)
                else:
                    options_string = ''
            except KeyError:
                options_string = ''

            embed.add_field(name=deleted_item['name'], value=options_string, inline=False)

        self.save_url_dict()
        response_with_view = await interaction.edit_original_response(embed=embed, view=self.get_menu_view())
        self.message_with_view_id = response_with_view.id
        self.interaction = False
        return

    async def info(self, interaction: ds.Interaction, service_name: str, url: str):
        service = self.services[service_name]
        selected_item = self.item_dict[service_name][url]

        embed = get_embed('상품 정보', None, color=service.SERVICE_COLOR,
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

        embed.add_field(name='URL', value=url, inline=False)

        response_with_view = await interaction.edit_original_response(embed=embed, view=self.get_menu_view())
        self.message_with_view_id = response_with_view.id
        self.interaction = False
        return

    async def list_(self, interaction: ds.Interaction):
        embeds = []

        for service_name, url_list in self.url_dict.items():
            if url_list:
                embed = get_embed(None, None,
                                  author=self.services[service_name].SERVICE_LABEL,
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
            await interaction.response.edit_message(embeds=embeds)
        else:
            await interaction.response.edit_message(embed=get_embed('상품 목록', '추가된 상품이 없습니다.'))

    async def on_ready(self):
        print(f'Logged in as {self.user.name} | {self.user.id}')
        print('Target user ID is', self.owner_id)
        owner = await self.get_or_fetch_user(self.owner_id)

        if owner.dm_channel is None:
            await owner.create_dm()

        self.target = owner.dm_channel

        if not self.initialized:
            items_count = 0
            for url_list in self.url_dict.values():
                items_count += len(url_list)

            if items_count:
                response_with_view = await self.target.send(
                    embed=get_embed("봇 시작됨", f'{items_count} 개의 상품을 확인 중입니다.'),
                    view=self.get_menu_view()
                )
            else:
                response_with_view = await self.target.send(embed=get_embed("봇 시작됨", f'추가된 상품이 없습니다.'),
                                                            view=self.get_menu_view())

            self.message_with_view_id = response_with_view.id
            self.initialized = True

    async def check_price(self):
        print('Starting price check loop...')
        while not self.is_ready():
            print('Waiting for bot to be ready...')
            await asyncio.sleep(1)
        if cfg['test_mode'] is True:
            print('Test mode enabled')
            while True:
                self.item_dict = {}
                await self.update_item_dict()
                for service_name, service_item_dict in self.item_dict.items():
                    for url, item in service_item_dict.items():
                        print(f'{item["name"]} | {item["price"]} | {url}')

                await asyncio.sleep(cfg['interval'])

        else:
            print('Loop is now starting...')
            while True:
                try:
                    last_dict = deepcopy(self.item_dict)
                    await self.update_item_dict()

                    embeds_to_send = []

                    for service_name, service_item_dict in self.item_dict.items():
                        try:
                            for url, item in service_item_dict.items():
                                last_item = last_dict[service_name][url]

                                if item != last_item:
                                    print('Item status changed:', item['name'], f"({url})")
                                    embed = get_embed(
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
                                                    item_value_string = '정보 없음'
                                                if not last_value:
                                                    last_value_string = '정보 없음'

                                                embed.add_field(
                                                    name=f'__{label}__',
                                                    value=f'__{last_value_string} -> {item_value_string}__',
                                                    inline=False)
                                                print(f'{key}: {last_value_string} -> {item_value_string}')
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
                                    embeds_to_send.append(embed)

                        except KeyError:  # New items
                            pass

                    if embeds_to_send:
                        if self.interaction:
                            print('Waiting for interaction to finish...')
                            while True:
                                if not self.interaction:
                                    await asyncio.sleep(3)
                                    break
                                await asyncio.sleep(1)

                        if len(embeds_to_send) <= 10:
                            await self.target.send(f'<@{self.owner_id}>', embeds=embeds_to_send)
                        else:
                            buffer = []
                            for i, embed in enumerate(embeds_to_send):
                                i += 1
                                buffer.append(embed)

                                if i % 10 == 0:
                                    await self.target.send(f'<@{self.owner_id}> 상품 정보 변동 알림', embeds=buffer)
                                    buffer = []

                        message_with_view = await self.target.fetch_message(self.message_with_view_id)

                        try:
                            await message_with_view.edit(view=None)
                        except ds.HTTPException:
                            await message_with_view.delete()

                        response_with_view = await self.target.send(view=self.get_menu_view())
                        self.message_with_view_id = response_with_view.id

                    await asyncio.sleep(cfg['interval'])

                except Exception as e:
                    print(f'Price check failed with exception {e}')
                    traceback.print_tb(e.__traceback__)
                    await asyncio.sleep(cfg['interval'])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print('Python version:', sys.version)

    if not os.path.isfile('config.json'):
        print('config.json not found. Creating new config file. Please fill in the required information.')
        reset_cfg()
    else:
        with open('config.json', 'r') as cfg_file:
            cfg = json.loads(cfg_file.read())

    if not os.path.isdir('cookies'):
        os.mkdir('cookies')

    bot = DiscordPriceBot()
    bot.run(cfg['token'])
