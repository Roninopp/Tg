#!/usr/bin/env python3
"""
Telegram Music Bot with Lavalink - ROBUST VERSION WITH DETAILED LOGGING
Works with: NTgCalls, py-tgcalls, or PyTgCalls
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Optional
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),  # Save to file
        logging.StreamHandler()  # Print to console
    ]
)
logger = logging.getLogger(__name__)

logger.info("="*60)
logger.info("BOT STARTING - LOADING CONFIGURATION")
logger.info("="*60)

# Import config
try:
    from config import API_ID, API_HASH, LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD
    logger.info(f"✓ Config loaded - API_ID: {API_ID}")
    
    # Check if using bot or userbot mode
    try:
        from config import BOT_TOKEN
        USE_USERBOT = False
        logger.info(f"✓ BOT_TOKEN found - Using BOT mode")
    except ImportError:
        BOT_TOKEN = None
        USE_USERBOT = True
        logger.info("✓ No BOT_TOKEN - Using USERBOT mode")
except ImportError as e:
    logger.error(f"❌ Error: config.py not found or incomplete! {e}")
    print("Please create config.py with your credentials")
    sys.exit(1)

# Detect which TgCalls library is available
TGCALLS_LIB = None
try:
    with open(".tgcalls_lib", "r") as f:
        TGCALLS_LIB = f.read().strip()
    logger.info(f"✓ Found TgCalls library marker: {TGCALLS_LIB}")
except:
    logger.warning("⚠ No .tgcalls_lib file found, will try to detect")

# Import appropriate library
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
        logger.error("❌ No TgCalls library found! Run install_dependencies.py first")
        sys.exit(1)

# Import Lavalink client
try:
    import aiohttp
    import json
    logger.info("✓ aiohttp imported")
except ImportError:
    logger.error("❌ aiohttp not found! Run: pip3 install aiohttp")
    sys.exit(1)

logger.info("="*60)
logger.info("INITIALIZING PYROGRAM CLIENT")
logger.info("="*60)

# Initialize Pyrogram client
if USE_USERBOT:
    app = Client(
        "music_userbot",
        api_id=API_ID,
        api_hash=API_HASH
    )
    logger.info("✓ Using USERBOT mode")
else:
    app = Client(
        "music_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    logger.info("✓ Using BOT mode")

# Initialize voice calls client
if TGCALLS_LIB == "ntgcalls":
    tgcalls = NTgCalls()
    logger.info("✓ NTgCalls client initialized")
else:
    tgcalls = PyTgCalls(app)
    logger.info("✓ PyTgCalls client initialized")

# Global variables
queues: Dict[int, list] = {}
current_playing: Dict[int, dict] = {}

logger.info("="*60)
logger.info("SETTING UP COMMAND HANDLERS")
logger.info("="*60)


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
        logger.info(f"✓ Lavalink client created: {self.base_url}")
    
    async def initialize(self):
        """Initialize session"""
        self.session = aiohttp.ClientSession()
        logger.info("✓ Lavalink session initialized")
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            logger.info("✓ Lavalink session closed")
    
    async def search(self, query: str):
        """Search for tracks"""
        try:
            search_query = f"ytsearch:{query}" if not query.startswith("http") else query
            logger.info(f"Searching Lavalink: {search_query[:50]}")
            
            async with self.session.get(
                f"{self.base_url}/v4/loadtracks",
                params={"identifier": search_query},
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✓ Lavalink search successful: {data.get('loadType')}")
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
                    url = data.get("uri")
                    logger.info(f"✓ Got stream URL: {url[:50] if url else 'None'}")
                    return url
                return None
        except Exception as e:
            logger.error(f"Stream URL error: {e}")
            return None


# Initialize Lavalink
lavalink = LavaLinkClient(LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD)


async def play_next(chat_id: int):
    """Play next song in queue"""
    logger.info(f"play_next called for chat {chat_id}")
    
    if chat_id not in queues or not queues[chat_id]:
        current_playing.pop(chat_id, None)
        try:
            if TGCALLS_LIB == "ntgcalls":
                await tgcalls.leave_call(chat_id)
            else:
                await tgcalls.leave_group_call(chat_id)
            logger.info(f"✓ Queue finished for {chat_id}, left voice chat")
        except Exception as e:
            logger.error(f"Error leaving voice chat: {e}")
        return
    
    # Get next song
    song = queues[chat_id].pop(0)
    current_playing[chat_id] = song
    logger.info(f"Playing next: {song['title']}")
    
    try:
        # Get stream URL from Lavalink
        stream_url = await lavalink.get_stream_url(song["track"])
        
        if not stream_url:
            logger.error("Failed to get stream URL")
            await play_next(chat_id)
            return
        
        # Start playing
        logger.info(f"Attempting to join voice chat {chat_id}")
        
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
        
        logger.info(f"✓ Now playing: {song['title']} in {chat_id}")
        
    except Exception as e:
        logger.error(f"Play error: {e}", exc_info=True)
        await play_next(chat_id)


# Debug handler - logs ALL messages
@app.on_message(filters.all)
async def debug_handler(client, message: Message):
    """Debug handler to see all incoming messages"""
    try:
        user_id = message.from_user.id if message.from_user else "None"
        chat_id = message.chat.id
        text = message.text or message.caption or "[no text]"
        
        logger.info("="*60)
        logger.info(f"MESSAGE RECEIVED:")
        logger.info(f"  From User: {user_id}")
        logger.info(f"  Chat ID: {chat_id}")
        logger.info(f"  Chat Type: {message.chat.type}")
        logger.info(f"  Text: {text[:100]}")
        logger.info(f"  Is Command: {bool(message.command)}")
        logger.info("="*60)
    except Exception as e:
        logger.error(f"Debug handler error: {e}")


@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Start command"""
    logger.info(f"⭐ START COMMAND from user {message.from_user.id} in chat {message.chat.id}")
    
    try:
        response = (
            "🎵 **Welcome to Music Bot!**\n\n"
            "**Commands:**\n"
            "/play <song name> - Play a song\n"
            "/pause - Pause current song\n"
            "/resume - Resume playback\n"
            "/skip - Skip current song\n"
            "/stop - Stop and clear queue\n"
            "/queue - Show queue\n"
            "/current - Show current song\n"
            "/ping - Test bot response\n\n"
            "**Powered by Lavalink**"
        )
        
        await message.reply_text(response)
        logger.info(f"✓ Sent start response to {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Start command error: {e}", exc_info=True)


@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Ping command for testing"""
    logger.info(f"⭐ PING COMMAND from user {message.from_user.id}")
    
    try:
        await message.reply_text("🏓 Pong! Bot is working!")
        logger.info(f"✓ Sent ping response")
    except Exception as e:
        logger.error(f"❌ Ping command error: {e}", exc_info=True)


@app.on_message(filters.command("play"))
async def play_command(client, message: Message):
    """Play command"""
    logger.info(f"⭐ PLAY COMMAND from user {message.from_user.id} in chat {message.chat.id}")
    logger.info(f"   Full message: {message.text}")
    
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ Usage: /play <song name or URL>")
            logger.warning("Play command without query")
            return
        
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        logger.info(f"   Query: {query}")
        logger.info(f"   Chat ID: {chat_id}")
        logger.info(f"   Chat type: {message.chat.type}")
        
        # Check if group
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply_text("❌ This command only works in groups!")
            logger.warning("Play command used in non-group chat")
            return
        
        status_msg = await message.reply_text("🔍 Searching...")
        logger.info("✓ Sent searching message")
        
        # Search using Lavalink
        result = await lavalink.search(query)
        
        if not result or result.get("loadType") == "error":
            await status_msg.edit_text("❌ No results found!")
            logger.error("No results from Lavalink")
            return
        
        # Get track info
        load_type = result.get("loadType")
        logger.info(f"✓ Load type: {load_type}")
        
        if load_type == "track":
            track = result["data"]
            tracks = [track]
        elif load_type == "search":
            tracks = result["data"][:1]
        elif load_type == "playlist":
            tracks = result["data"]["tracks"][:10]
        else:
            await status_msg.edit_text("❌ Could not load track!")
            return
        
        if not tracks:
            await status_msg.edit_text("❌ No tracks found!")
            return
        
        logger.info(f"✓ Found {len(tracks)} track(s)")
        
        # Add to queue
        if chat_id not in queues:
            queues[chat_id] = []
        
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
            logger.info(f"   Added to queue: {song_info['title']}")
        
        # Start playing if nothing is playing
        if chat_id not in current_playing:
            await status_msg.edit_text(f"▶️ Playing: **{tracks[0]['info']['title']}**")
            logger.info(f"✓ Starting playback")
            await play_next(chat_id)
        else:
            await status_msg.edit_text(
                f"✅ Added to queue:\n**{tracks[0]['info']['title']}**"
            )
            logger.info(f"✓ Added to queue (already playing)")
    
    except Exception as e:
        logger.error(f"❌ Play command error: {e}", exc_info=True)
        try:
            await message.reply_text(f"❌ Error: {str(e)}")
        except:
            pass


@app.on_message(filters.command("pause"))
async def pause_command(client, message: Message):
    """Pause command"""
    logger.info(f"⭐ PAUSE COMMAND from user {message.from_user.id}")
    
    try:
        chat_id = message.chat.id
        
        if chat_id not in current_playing:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.pause(chat_id)
        else:
            await tgcalls.pause_stream(chat_id)
        
        await message.reply_text("⏸ Paused")
        logger.info("✓ Paused playback")
        
    except Exception as e:
        logger.error(f"❌ Pause error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("resume"))
async def resume_command(client, message: Message):
    """Resume command"""
    logger.info(f"⭐ RESUME COMMAND from user {message.from_user.id}")
    
    try:
        chat_id = message.chat.id
        
        if chat_id not in current_playing:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.resume(chat_id)
        else:
            await tgcalls.resume_stream(chat_id)
        
        await message.reply_text("▶️ Resumed")
        logger.info("✓ Resumed playback")
        
    except Exception as e:
        logger.error(f"❌ Resume error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("skip"))
async def skip_command(client, message: Message):
    """Skip command"""
    logger.info(f"⭐ SKIP COMMAND from user {message.from_user.id}")
    
    try:
        chat_id = message.chat.id
        
        if chat_id not in current_playing:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        await message.reply_text("⏭ Skipped")
        logger.info("✓ Skipping to next track")
        await play_next(chat_id)
        
    except Exception as e:
        logger.error(f"❌ Skip error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("stop"))
async def stop_command(client, message: Message):
    """Stop command"""
    logger.info(f"⭐ STOP COMMAND from user {message.from_user.id}")
    
    try:
        chat_id = message.chat.id
        
        if chat_id not in current_playing:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        queues.pop(chat_id, None)
        current_playing.pop(chat_id, None)
        
        if TGCALLS_LIB == "ntgcalls":
            await tgcalls.leave_call(chat_id)
        else:
            await tgcalls.leave_group_call(chat_id)
        
        await message.reply_text("⏹ Stopped and cleared queue")
        logger.info("✓ Stopped playback and cleared queue")
        
    except Exception as e:
        logger.error(f"❌ Stop error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


@app.on_message(filters.command("queue"))
async def queue_command(client, message: Message):
    """Show queue"""
    logger.info(f"⭐ QUEUE COMMAND from user {message.from_user.id}")
    
    try:
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
        logger.info(f"✓ Sent queue ({len(queues[chat_id])} songs)")
        
    except Exception as e:
        logger.error(f"❌ Queue error: {e}", exc_info=True)


@app.on_message(filters.command("current"))
async def current_command(client, message: Message):
    """Show current song"""
    logger.info(f"⭐ CURRENT COMMAND from user {message.from_user.id}")
    
    try:
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
        logger.info("✓ Sent current playing info")
        
    except Exception as e:
        logger.error(f"❌ Current error: {e}", exc_info=True)


async def main():
    """Main function"""
    logger.info("="*60)
    logger.info("MAIN FUNCTION STARTING")
    logger.info("="*60)
    
    # Initialize Lavalink client
    await lavalink.initialize()
    
    # Test Lavalink connection
    try:
        logger.info("Testing Lavalink connection...")
        async with lavalink.session.get(
            f"{lavalink.base_url}/version",
            headers=lavalink.headers,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            if resp.status == 200:
                version = await resp.text()
                logger.info(f"✓ Connected to Lavalink: {version}")
            else:
                logger.error(f"❌ Lavalink returned status: {resp.status}")
                await lavalink.close()
                return
    except Exception as e:
        logger.error(f"❌ Lavalink connection failed: {e}")
        logger.error("Make sure Lavalink is running: cd lavalink && java -jar Lavalink.jar")
        await lavalink.close()
        return
    
    # Start TgCalls
    if TGCALLS_LIB != "ntgcalls":
        logger.info("Starting PyTgCalls...")
        await tgcalls.start()
        logger.info("✓ PyTgCalls started")
    
    logger.info("="*60)
    logger.info("✓ BOT READY - STARTING PYROGRAM")
    logger.info("="*60)
    logger.info("Bot will now respond to commands!")
    logger.info("Try: /start or /ping")
    logger.info("="*60)
    
    # Start app
    await app.start()
    
    me = await app.get_me()
    logger.info(f"✓ Logged in as: {me.first_name} (@{me.username})")
    logger.info(f"✓ Bot ID: {me.id}")
    
    # Keep alive
    from pyrogram import idle
    await idle()
    
    # Cleanup
    logger.info("Shutting down...")
    await app.stop()
    await lavalink.close()


if __name__ == "__main__":
    try:
        logger.info("="*60)
        logger.info("STARTING BOT APPLICATION")
        logger.info("="*60)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n✓ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
