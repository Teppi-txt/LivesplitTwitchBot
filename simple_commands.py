import twitchio
from twitchio.ext import commands
from twitchio.ext.commands import Bot


class SimpleCommands(commands.Component):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

    @commands.command()
    async def title(self, ctx: commands.Context) -> None:
        await ctx.reply((await ctx.broadcaster.fetch_channel_info()).title)

    @commands.command()
    async def ping(self, ctx: commands.Context) -> None:
        await ctx.reply("pong");

