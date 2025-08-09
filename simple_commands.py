import asyncio

import twitchio
from dotenv import dotenv_values
from twitchio.ext import commands
from twitchio.ext.commands import Bot

from Formatter import *


class Redeems(commands.Component):
    config = dotenv_values('.env')

    @commands.reward_command(id=config["RENAME_CURRENT_SPLIT_REDEEM_ID"], invoke_when=commands.RewardStatus.all)
    async def rename_current_split(self, ctx: commands.Context, *, user_input: str) -> None:
        reader, writer = await asyncio.open_connection('localhost', 16834)
        writer.write(("setcurrentsplitname " + user_input + "\n").encode('UTF-8'))
        await writer.drain()

        writer.write(b"getcurrentsplitname\n")
        await writer.drain()

        response = await reader.readline()

        writer.close()
        await writer.wait_closed()

        await ctx.send("Attempted to rename " + response.decode('UTF-8') + " to " + user_input)


class NonIntrusiveCommands(commands.Component):

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
        await ctx.reply("pong")

    @commands.command()
    async def splitinfo(self, ctx: commands.Context) -> None:
        reader, writer = await asyncio.open_connection('localhost', 16834)
        writer.write(b"getcurrentsplitname\n")
        await writer.drain()

        response = await reader.readline()

        writer.close()
        await writer.wait_closed()

        if response == "-":
            await ctx.reply(f"Livesplit is currently inactive.")
        else:
            await ctx.reply(f"{response.decode().strip()}")

    @commands.command()
    async def pace(self, ctx: commands.Context) -> None:
        reader, writer = await asyncio.open_connection('localhost', 16834)
        writer.write((b"getdelta Personal Best\n"))
        await writer.drain()

        delta_pb = await reader.readline()
        delta_pb = parse_duration(delta_pb.decode('UTF-8'))

        writer.write((b"getdelta Best Split Times\n"))
        await writer.drain()

        delta_best = await reader.readline()
        delta_best = parse_duration(delta_best.decode('UTF-8'))

        writer.close()
        await writer.wait_closed()

        if delta_pb == "-":
            await ctx.reply(f"Cannot compare pace while livesplit is inactive or on the first split.")
        else:
            await ctx.reply("Current pace is " + delta_pb + " to PB and " + delta_best + " to best pace ever.")



class IntrusiveCommands(commands.Component):
    @commands.command()
    async def livesplit(self, ctx: commands.Context, command: str) -> None:
        reader, writer = await asyncio.open_connection('localhost', 16834)
        writer.write((command + "\n").encode('UTF-8'))
        await writer.drain()

        response = await reader.readline()

        writer.close()
        await writer.wait_closed()

        if response == "-":
            await ctx.reply(f"Livesplit is currently inactive.")
        else:
            await ctx.reply(f"Server said: {response.decode().strip()}")
