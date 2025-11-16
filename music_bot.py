#!/usr/bin/env python3
"""
Telegram Music Bot with Lavalink - FIXED HANDLER VERSION
Handlers registered AFTER client starts (like your working play.py)
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)

logger.info("="*60)
logger.info("MUSIC BOT STARTING")
logger.info("="*60)

# Import config
try:
    from config import API_ID, API_HASH, LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD
    logger.info(f"✓ Config loaded - API_ID: {API_ID}")
    
    try:
        from config import BOT_TOKEN
        USE_USERBOT = False
        logger.info(f"✓ Using BOT mode")
    except ImportError:
        BOT_TOKEN = None
        USE_USERBOT = True
        logger.info("✓ Using USERBOT mode")
except ImportError as e:
    logger.error(f"❌ Config error: {e}")
    sys.exit(1)

# Detect TgCalls library
TGCALLS_LIB = None
try:
    with open(".tgcalls_lib", "r") as f:
        TGCALLS_LIB = f.read().strip()
except:
    pass

if TGCALLS_LIB == "ntgcalls":
    try:
        from ntgcalls import NTgCalls
        logger.info("✓ Using NTgCalls")
    except ImportError:
        logger.error("❌ NTgCalls not found!")
        sys.exit(1)
else:
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types import MediaStream
        logger.info("✓ Using PyTgCalls")
        TGCALLS_LIB = "pytgcalls"
    except ImportError:
        logger.error("❌ No TgCalls library found!")
        sys.exit(1)

try:
    import aiohttp
except ImportError:
    logger.error("❌ aiohttp not found!")
    sys.exit(1)

# Initialize client WITHOUT plugins parameter
if USE_USERBOT:
    app = Client("music_userbot", api_id=API_ID, api_hash=API_HASH)
else:
    app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize TgCalls
if TGCALLS_LIB == "ntgcalls":
    tgcalls = NTgCalls()
else:
    tgcalls = PyTgCalls(app)

# Global variables
queues: Dict[int, list] = {}
current_playing: Dict[int, dict] = {}


class LavaLinkClient:
    """Lavalink client"""
    
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.session = None
        self.headers = {"Authorization": password, "Content-Type": "application/json"}
    
    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info("✓ Lavalink session initialized")
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def search(self, query: str):
        try:
            search_query = f"ytsearch:{query}" if not query.startswith("http") else query
            async with self.session.get(
                f"{self.base_url}/v4/loadtracks",
                params={"identifier": search_query},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_stream_url(self, track_encoded: str):
        try:
            async with self.session.get(
                f"{self.base_url}/v4/decodetrack",
                params={"encodedTrack": track_encoded},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("uri")
                return None
        except Exception as e:
            logger.error(f"Stream URL error: {e}")
            return None


lavalink = LavaLinkClient(LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD)


async def play_next(chat_id: int):
    """Play next song"""
    if chat_id not in queues or not queues[chat_id]:
        current_playing.pop(chat_id, None)
        try:
            if TGCALLS_LIB == "ntgcalls":
                await tgcalls.leave_call(chat_id)
            else:
                await tgcalls.leave_group_call(chat_id)
        except:
            pass
        return
    
    song = queues[chat_id].pop(0)
    current_playing[chat_id] = song
    
    try:
        stream_url = await lavalink.get_stream_url(song["track"])
        if not stream_url:
            await play_next(chat_id)
            return
        
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.join_call(chat_id, stream_url, stream_type="audio")
        else:
            await tgcalls.join_group_call(chat_id, MediaStream(stream_url))
        
        logger.info(f"✓ Playing: {song['title']}")
    except Exception as e:
        logger.error(f"Play error: {e}")
        await play_next(chat_id)


# ============================================
# COMMAND HANDLERS - REGISTERED AFTER START
# ============================================

async def start_handler(client, message: Message):
    """Start command"""
    logger.info(f"⭐ START from {message.from_user.id}")
    try:
        await message.reply_text(
            "🎵 **Welcome to Music Bot!**\n\n"
            "**Commands:**\n"
            "/play <song> - Play music\n"
            "/pause - Pause\n"
            "/resume - Resume\n"
            "/skip - Skip\n"
            "/stop - Stop\n"
            "/queue - Show queue\n"
            "/current - Current song\n"
            "/ping - Test bot\n\n"
            "**Powered by Lavalink**"
        )
        logger.info("✓ Sent start message")
    except Exception as e:
        logger.error(f"Start error: {e}")


async def ping_handler(client, message: Message):
    """Ping command"""
    logger.info(f"⭐ PING from {message.from_user.id}")
    try:
        await message.reply_text("🏓 **Pong!** Bot is working!")
        logger.info("✓ Sent ping response")
    except Exception as e:
        logger.error(f"Ping error: {e}")


async def play_handler(client, message: Message):
    """Play command"""
    logger.info(f"⭐ PLAY from {message.from_user.id}: {message.text}")
    
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ Usage: /play <song name>")
            return
        
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply_text("❌ This works in groups only!")
            return
        
        status = await message.reply_text("🔍 Searching...")
        
        result = await lavalink.search(query)
        if not result or result.get("loadType") == "error":
            await status.edit_text("❌ No results found!")
            return
        
        load_type = result.get("loadType")
        
        if load_type == "track":
            tracks = [result["data"]]
        elif load_type == "search":
            tracks = result["data"][:1]
        elif load_type == "playlist":
            tracks = result["data"]["tracks"][:10]
        else:
            await status.edit_text("❌ Could not load track!")
            return
        
        if not tracks:
            await status.edit_text("❌ No tracks found!")
            return
        
        if chat_id not in queues:
            queues[chat_id] = []
        
        for track in tracks:
            info = track.get("info", {})
            queues[chat_id].append({
                "title": info.get("title", "Unknown"),
                "author": info.get("author", "Unknown"),
                "duration": info.get("length", 0),
                "track": track.get("encoded"),
                "requester": message.from_user.mention
            })
        
        if chat_id not in current_playing:
            await status.edit_text(f"▶️ Playing: **{tracks[0]['info']['title']}**")
            await play_next(chat_id)
        else:
            await status.edit_text(f"✅ Added: **{tracks[0]['info']['title']}**")
        
        logger.info(f"✓ Added {len(tracks)} track(s)")
        
    except Exception as e:
        logger.error(f"Play error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {e}")


async def pause_handler(client, message: Message):
    """Pause command"""
    logger.info(f"⭐ PAUSE from {message.from_user.id}")
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing playing!")
        return
    
    try:
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.pause(chat_id)
        else:
            await tgcalls.pause_stream(chat_id)
        await message.reply_text("⏸ Paused")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


async def resume_handler(client, message: Message):
    """Resume command"""
    logger.info(f"⭐ RESUME from {message.from_user.id}")
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing playing!")
        return
    
    try:
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.resume(chat_id)
        else:
            await tgcalls.resume_stream(chat_id)
        await message.reply_text("▶️ Resumed")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


async def skip_handler(client, message: Message):
    """Skip command"""
    logger.info(f"⭐ SKIP from {message.from_user.id}")
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing playing!")
        return
    
    await message.reply_text("⏭ Skipped")
    await play_next(chat_id)


async def stop_handler(client, message: Message):
    """Stop command"""
    logger.info(f"⭐ STOP from {message.from_user.id}")
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing playing!")
        return
    
    queues.pop(chat_id, None)
    current_playing.pop(chat_id, None)
    
    try:
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.leave_call(chat_id)
        else:
            await tgcalls.leave_group_call(chat_id)
        await message.reply_text("⏹ Stopped")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


async def queue_handler(client, message: Message):
    """Queue command"""
    chat_id = message.chat.id
    
    if chat_id not in queues or not queues[chat_id]:
        await message.reply_text("📭 Queue is empty")
        return
    
    text = "📜 **Queue:**\n\n"
    for i, song in enumerate(queues[chat_id][:10], 1):
        dur = song["duration"] // 1000
        text += f"{i}. **{song['title']}**\n   {song['author']} | {dur//60}:{dur%60:02d}\n\n"
    
    if len(queues[chat_id]) > 10:
        text += f"...and {len(queues[chat_id]) - 10} more"
    
    await message.reply_text(text)


async def current_handler(client, message: Message):
    """Current command"""
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing playing!")
        return
    
    song = current_playing[chat_id]
    dur = song["duration"] // 1000
    
    await message.reply_text(
        f"🎵 **Now Playing:**\n\n"
        f"**{song['title']}**\n"
        f"👤 {song['author']}\n"
        f"⏱ {dur//60}:{dur%60:02d}\n"
        f"👤 By: {song['requester']}"
    )


async def main():
    """Main function"""
    logger.info("Initializing...")
    
    # Initialize Lavalink
    await lavalink.initialize()
    
    # Test Lavalink
    try:
        async with lavalink.session.get(f"{lavalink.base_url}/version", headers=lavalink.headers) as resp:
            if resp.status == 200:
                version = await resp.text()
                logger.info(f"✓ Lavalink: {version}")
            else:
                logger.error("❌ Can't connect to Lavalink!")
                await lavalink.close()
                return
    except Exception as e:
        logger.error(f"❌ Lavalink error: {e}")
        logger.error("Start Lavalink first: cd lavalink && java -jar Lavalink.jar")
        await lavalink.close()
        return
    
    # Start PyTgCalls if needed
    if TGCALLS_LIB != "ntgcalls":
        await tgcalls.start()
    
    # Start Pyrogram
    await app.start()
    
    me = await app.get_me()
    logger.info(f"✓ Logged in as: {me.first_name} (@{me.username})")
    
    # ============================================
    # REGISTER HANDLERS AFTER START (KEY FIX!)
    # ============================================
    logger.info("Registering command handlers...")
    
    app.add_handler(MessageHandler(start_handler, filters.command("start")))
    app.add_handler(MessageHandler(ping_handler, filters.command("ping")))
    app.add_handler(MessageHandler(play_handler, filters.command("play")))
    app.add_handler(MessageHandler(pause_handler, filters.command("pause")))
    app.add_handler(MessageHandler(resume_handler, filters.command("resume")))
    app.add_handler(MessageHandler(skip_handler, filters.command("skip")))
    app.add_handler(MessageHandler(stop_handler, filters.command("stop")))
    app.add_handler(MessageHandler(queue_handler, filters.command("queue")))
    app.add_handler(MessageHandler(current_handler, filters.command("current")))
    
    logger.info("✓ All handlers registered!")
    logger.info("="*60)
    logger.info("✅ BOT IS READY!")
    logger.info("Try: /start or /ping")
    logger.info("="*60)
    
    # Keep alive
    from pyrogram import idle
    await idle()
    
    # Cleanup
    await app.stop()
    await lavalink.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n✓ Bot stopped")
