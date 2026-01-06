import discord
from discord.ext import commands
import asyncio
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

TARGET_GUILD_ID = 1456923770261471353
TARGET_CHANNEL_ID = 1458156459266408641

active_forwarding = {}

async def get_webhook(channel: discord.TextChannel):
    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name="Full Channel Mirror")
    if webhook is None:
        webhook = await channel.create_webhook(name="Full Channel Mirror")
    return webhook

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    print("Ready to fully mirror channels!")

async def forward_full_history(source_channel: discord.TextChannel, webhook: discord.Webhook, status_message: discord.Message):
    total_forwarded = 0
    last_message_id = None
    start_time = datetime.datetime.now()

    await status_message.edit(content="🔄 **Starting full channel mirror...** (fetching all history)")

    while True:
        try:
            history_chunk = source_channel.history(
                limit=100,
                before=discord.Object(id=last_message_id) if last_message_id else None,
                oldest_first=False
            )
            messages = [msg async for msg in history_chunk]

            if not messages:
                break

            messages.reverse()  # oldest first

            for message in messages:
                if message.author.bot and message.author != bot.user:
                    continue  # skip other bots

                try:
                    content = message.content or " "
                    files = [await att.to_file(spoiler=att.is_spoiler()) for att in message.attachments][:10]

                    await webhook.send(
                        content=content,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url,
                        embeds=message.embeds,
                        files=files,
                        allowed_mentions=discord.AllowedMentions.none(),
                        wait=True
                    )
                    total_forwarded += 1

                    if total_forwarded % 50 == 0:
                        elapsed = datetime.datetime.now() - start_time
                        await status_message.edit(
                            content=f"🔄 Mirroring...\nForwarded: **{total_forwarded}** messages\nElapsed: {str(elapsed).split('.')[0]}"
                        )

                except Exception as e:
                    print(f"Failed message {message.id}: {e}")

                await asyncio.sleep(0.6)

            if len(messages) < 100:
                break
            last_message_id = messages[0].id

        except Exception as e:
            print(f"History fetch error: {e}")
            await asyncio.sleep(5)

    elapsed = datetime.datetime.now() - start_time
    return total_forwarded, elapsed

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.content.strip() == '.send':
        if message.channel.id in active_forwarding:
            await message.channel.send("⚠️ Already mirroring this channel!")
            return

        target_guild = bot.get_guild(TARGET_GUILD_ID)
        if not target_guild:
            await message.channel.send("❌ Bot not in target server.")
            return

        target_channel = target_guild.get_channel(TARGET_CHANNEL_ID)
        if not isinstance(target_channel, discord.TextChannel):
            await message.channel.send("❌ Target channel not found.")
            return

        webhook = await get_webhook(target_channel)
        if not webhook:
            await message.channel.send("❌ Could not create webhook.")
            return

        status_msg = await message.channel.send("⏳ Preparing full mirror...")

        active_forwarding[message.channel.id] = webhook

        total, time_taken = await forward_full_history(message.channel, webhook, status_msg)

        await status_msg.edit(
            content=f"✅ **Full mirror done!**\n"
                    f"Forwarded **{total}** messages\n"
                    f"Time: {str(time_taken).split('.')[0]}\n\n"
                    f"🔴 Live forwarding active → new messages will appear instantly.\n"
                    f"Use `.stop` to stop live forwarding."
        )
        return

    if message.content.strip() == '.stop':
        if message.channel.id in active_forwarding:
            del active_forwarding[message.channel.id]
            await message.channel.send("🛑 Live forwarding stopped.")
        else:
            await message.channel.send("ℹ️ Nothing to stop here.")
        return

    if message.channel.id in active_forwarding:
        webhook = active_forwarding[message.channel.id]
        try:
            files = [await att.to_file(spoiler=att.is_spoiler()) for att in message.attachments][:10]
            await webhook.send(
                content=message.content or " ",
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                embeds=message.embeds,
                files=files,
                allowed_mentions=discord.AllowedMentions.none(),
                wait=True
            )
        except Exception as e:
            print(f"Live forward error: {e}")

    await bot.process_commands(message)

# === PUT YOUR NEW TOKEN HERE AFTER RESETTING ===
bot.run('MTQ1ODE2MTI1MDc4MDQ0Njc4MA.GCw9f5.P7ozEfRgicAbV0sMfxBjEkmN69Q-4tpEwvNTJA')
