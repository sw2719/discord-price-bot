from discord import Embed  # noqa
from typing import Union


def get_embed(title: Union[str, None], description: Union[str, None], color: int = 0x7289da,
              author: str = '', icon: str = '', footer: str = '', url=None) -> Embed:
    embed = Embed(title=title, description=description, color=color, url=url)

    if footer:
        embed.set_footer(text=footer)

    if author:
        if icon:
            embed.set_author(name=author, icon_url=icon)
        else:
            embed.set_author(name=author)

    return embed
