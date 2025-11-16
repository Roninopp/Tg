#!/usr/bin/env python3
"""
Telegram Music Bot with Lavalink
Works with: NTgCalls, py-tgcalls, or PyTgCalls
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

# Import config
try:
    from config import API_ID, API_HASH, LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD
    # Check if using bot or userbot mode
    try:
        from config import BOT_TOKEN
        USE_USERBOT = False
    except ImportError:
        BOT_TOKEN = None
        USE_USERBOT = True
except ImportError:
    print("❌ Error: config.py not found!")
    print("Please create config.py with your credentials")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Detect which TgCalls library is available
TGCALLS_LIB = None
try:
    with open(".tgcalls_lib", "r") as f:
        TGCALLS_LIB = f.read().strip()
except:
    pass

# Import appropriate library
if TGCALLS_LIB == "ntgcalls":
    try:
        from ntgcalls import NTgCalls
        logger.info("✓ Using NTgCalls")
    except ImportError:
        logger.error("NTgCalls not found!")
        sys.exit(1)
else:
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types import MediaStream
        logger.info("✓ Using PyTgCalls")
        TGCALLS_LIB = "pytgcalls"
    except ImportError:
        logger.error("No TgCalls library found! Run install_dependencies.py first")
        sys.exit(1)

# Import Lavalink client
try:
    import aiohttp
    import json
except ImportError:
    logger.error("aiohttp not found! Run: pip3 install aiohttp")
    sys.exit(1)

# Initialize Pyrogram client
if USE_USERBOT:
    # Userbot mode - will ask for phone number or use session
    app = Client(
        "music_userbot",
        api_id=API_ID,
        api_hash=API_HASH
    )
    logger.info("Using USERBOT mode")
else:
    # Bot mode
    app = Client(
        "music_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    logger.info("Using BOT mode")

# Initialize voice calls client
if TGCALLS_LIB == "ntgcalls":
    tgcalls = NTgCalls()
else:
    tgcalls = PyTgCalls(app)

# Global variables
queues: Dict[int, list] = {}  # chat_id: [songs]
current_playing: Dict[int, dict] = {}  # chat_id: song_info


class LavaLinkClient:
    """Simple Lavalink client"""
    
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.session = None
        self.headers = {
            "Authorization": password,
            "Content-Type": "application/json"
        }
    
    async def initialize(self):
        """Initialize session"""
        self.session = aiohttp.ClientSession()
        logger.info("✓ Lavalink client initialized")
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def search(self, query: str):
        """Search for tracks"""
        try:
            search_query = f"ytsearch:{query}" if not query.startswith("http") else query
            
            async with self.session.get(
                f"{self.base_url}/v4/loadtracks",
                params={"identifier": search_query},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    logger.error(f"Lavalink error: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_stream_url(self, track_encoded: str):
        """Get direct stream URL for track"""
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

# Initialize Lavalink
lavalink = LavaLinkClient(LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD)


async def play_next(chat_id: int):
    """Play next song in queue"""
    if chat_id not in queues or not queues[chat_id]:
        current_playing.pop(chat_id, None)
        try:
            if TGCALLS_LIB == "ntgcalls":
                await tgcalls.leave_call(chat_id)
            else:
                await tgcalls.leave_group_call(chat_id)
            logger.info(f"Queue finished for {chat_id}")
        except:
            pass
        return
    
    # Get next song
    song = queues[chat_id].pop(0)
    current_playing[chat_id] = song
    
    try:
        # Get stream URL from Lavalink
        stream_url = await lavalink.get_stream_url(song["track"])
        
        if not stream_url:
            logger.error("Failed to get stream URL")
            await play_next(chat_id)
            return
        
        # Start playing
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.join_call(
                chat_id,
                stream_url,
                stream_type="audio"
            )
        else:
            await tgcalls.join_group_call(
                chat_id,
                MediaStream(stream_url)
            )
        
        logger.info(f"Playing: {song['title']} in {chat_id}")
        
    except Exception as e:
        logger.error(f"Play error: {e}")
        await play_next(chat_id)


@app.on_message(filters.command("start") & (filters.private | filters.group))
async def start_command(client, message: Message):
    """Start command"""
    try:
        await message.reply_text(
            "🎵 **Welcome to Music Bot!**\n\n"
            "**Commands:**\n"
            "/play <song name> - Play a song\n"
            "/pause - Pause current song\n"
            "/resume - Resume playback\n"
            "/skip - Skip current song\n"
            "/stop - Stop and clear queue\n"
            "/queue - Show queue\n"
            "/current - Show current song\n\n"
            "**Powered by Lavalink**"
        )
        logger.info(f"Start command from {message.from_user.id}")
    except Exception as e:
        logger.error(f"Start command error: {e}")


@app.on_message(filters.command("play") & (filters.private | filters.group))
async def play_command(client, message: Message):
    """Play command"""
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ Usage: /play <song name or URL>")
            return
        
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        logger.info(f"Play command: {query} from chat {chat_id}")
        
        # Check if user is in voice chat
        try:
            chat = await client.get_chat(chat_id)
            if not chat.type in ["group", "supergroup"]:
                await message.reply_text("❌ This command only works in groups!")
                return
        except:
            pass
        
        status_msg = await message.reply_text("🔍 Searching...")
        
        try:
            # Search using Lavalink
            result = await lavalink.search(query)
            
            if not result or result.get("loadType") == "error":
                await status_msg.edit_text("❌ No results found!")
                return
            
            # Get track info
            load_type = result.get("loadType")
            
            if load_type == "track":
                track = result["data"]
                tracks = [track]
            elif load_type == "search":
                tracks = result["data"][:1]  # Take first result
            elif load_type == "playlist":
                tracks = result["data"]["tracks"][:10]  # Limit to 10
            else:
                await status_msg.edit_text("❌ Could not load track!")
                return
            
            if not tracks:
                await status_msg.edit_text("❌ No tracks found!")
                return
            
            # Add to queue
            if chat_id not in queues:
                queues[chat_id] = []
            
            added_count = 0
            for track in tracks:
                info = track.get("info", {})
                song_info = {
                    "title": info.get("title", "Unknown"),
                    "author": info.get("author", "Unknown"),
                    "duration": info.get("length", 0),
                    "track": track.get("encoded"),
                    "requester": message.from_user.mention
                }
                queues[chat_id].append(song_info)
                added_count += 1
            
            # Start playing if nothing is playing
            if chat_id not in current_playing:
                await status_msg.edit_text(f"▶️ Playing: **{tracks[0]['info']['title']}**")
                await play_next(chat_id)
            else:
                if added_count == 1:
                    await status_msg.edit_text(
                        f"✅ Added to queue:\n**{tracks[0]['info']['title']}**\n"
                        f"Position: {len(queues[chat_id])}"
                    )
                else:
                    await status_msg.edit_text(
                        f"✅ Added {added_count} songs to queue"
                    )
        
        except Exception as e:
            logger.error(f"Play error: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)}")
    except Exception as e:
        logger.error(f"Play command error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("pause") & filters.group)
async def pause_command(client, message: Message):
    """Pause command"""
    try:
        chat_id = message.chat.id
        
        if chat_id not in current_playing:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        try:
            if TGCALLS_LIB == "ntgcalls":
                await tgcalls.pause(chat_id)
            else:
                await tgcalls.pause_stream(chat_id)
            await message.reply_text("⏸ Paused")
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
    except Exception as e:
        logger.error(f"Pause command error: {e}")


@app.on_message(filters.command("resume"))
async def resume_command(client, message: Message):
    """Resume command"""
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing is playing!")
        return
    
    try:
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.resume(chat_id)
        else:
            await tgcalls.resume_stream(chat_id)
        await message.reply_text("▶️ Resumed")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("skip"))
async def skip_command(client, message: Message):
    """Skip command"""
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing is playing!")
        return
    
    await message.reply_text("⏭ Skipped")
    await play_next(chat_id)


@app.on_message(filters.command("stop"))
async def stop_command(client, message: Message):
    """Stop command"""
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing is playing!")
        return
    
    queues.pop(chat_id, None)
    current_playing.pop(chat_id, None)
    
    try:
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.leave_call(chat_id)
        else:
            await tgcalls.leave_group_call(chat_id)
        await message.reply_text("⏹ Stopped and cleared queue")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("queue"))
async def queue_command(client, message: Message):
    """Show queue"""
    chat_id = message.chat.id
    
    if chat_id not in queues or not queues[chat_id]:
        await message.reply_text("📭 Queue is empty")
        return
    
    queue_text = "📜 **Queue:**\n\n"
    for i, song in enumerate(queues[chat_id][:10], 1):
        duration = song["duration"] // 1000
        queue_text += f"{i}. **{song['title']}**\n"
        queue_text += f"   👤 {song['author']} | ⏱ {duration//60}:{duration%60:02d}\n\n"
    
    if len(queues[chat_id]) > 10:
        queue_text += f"...and {len(queues[chat_id]) - 10} more"
    
    await message.reply_text(queue_text)


@app.on_message(filters.command("current"))
async def current_command(client, message: Message):
    """Show current song"""
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply_text("❌ Nothing is playing!")
        return
    
    song = current_playing[chat_id]
    duration = song["duration"] // 1000
    
    text = (
        f"🎵 **Now Playing:**\n\n"
        f"**{song['title']}**\n"
        f"👤 {song['author']}\n"
        f"⏱ Duration: {duration//60}:{duration%60:02d}\n"
        f"👤 Requested by: {song['requester']}"
    )
    
    await message.reply_text(text)


async def main():
    """Main function"""
    logger.info("Starting Music Bot...")
    
    # Initialize Lavalink client
    await lavalink.initialize()
    
    # Test Lavalink connection
    try:
        async with lavalink.session.get(
            f"{lavalink.base_url}/version",
            headers=lavalink.headers
        ) as resp:
            if resp.status == 200:
                version = await resp.text()
                logger.info(f"✓ Connected to Lavalink: {version}")
            else:
                logger.error("❌ Cannot connect to Lavalink!")
                logger.error("Make sure Lavalink is running on localhost:2333")
                await lavalink.close()
                return
    except Exception as e:
        logger.error(f"❌ Lavalink connection failed: {e}")
        logger.error("Run lavalink_setup.py first and start Lavalink!")
        await lavalink.close()
        return
    
    # Start TgCalls
    if TGCALLS_LIB != "ntgcalls":
        await tgcalls.start()
    
    logger.info("✓ Bot started successfully!")
    logger.info("Press Ctrl+C to stop")
    
    # Add message handler for debugging
    @app.on_message(filters.text)
    async def message_handler(client, message):
        logger.info(f"Received message from {message.from_user.id}: {message.text[:50]}")
    
    # Start app
    await app.start()
    
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
