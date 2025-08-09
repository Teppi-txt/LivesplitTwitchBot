import asyncio
import logging
from typing import TYPE_CHECKING

import asqlite
import twitchio
from twitchio import eventsub
from twitchio.ext import commands

import simple_commands
from dotenv import dotenv_values

if TYPE_CHECKING:
    import sqlite3


LOGGER: logging.Logger = logging.getLogger("Bot")

config = dotenv_values('.env')

class Bot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]) -> None:
        self.token_database = token_database


        super().__init__(
            client_id=config['CLIENT_ID'],
            client_secret=config["CLIENT_SECRET"],
            bot_id=config['BOT_ID'],
            owner_id=config['OWNER_ID'],
            prefix="!",
            subscriptions=subs,
        )

    async def setup_hook(self) -> None:
        await self.add_component(simple_commands.NonIntrusiveCommands(self))
        await self.add_component(simple_commands.IntrusiveCommands(self))
        await self.add_component(simple_commands.Redeems(self))

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            return

        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
            eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
            eventsub.ChannelPointsRedeemUpdateSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id)
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)

async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist..
    # You should add the created files to .gitignore or potentially store them somewhere safer
    # This is just for example purposes...

    query = """CREATE TABLE IF NOT EXISTS tokens(
                    user_id TEXT PRIMARY KEY, 
                    token TEXT NOT NULL, 
                    refresh TEXT NOT NULL)"""

    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens...
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))
            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=config['BOT_ID'])])

    return tokens, subs

def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)

            async with Bot(token_database=tdb, subs=subs) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)

                await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())

    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")

async def get_ids() -> None:
    async with twitchio.Client(client_id=config['CLIENT_ID'], client_secret=config['CLIENT_SECRET']) as client:
        await client.login()
        user = await client.fetch_users(logins=["twitchteppi", "TeppiBot"])
        for u in user:
            print(f"User: {u.name} - ID: {u.id}")

if __name__ == "__main__":
    main()
