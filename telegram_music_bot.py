import os
import sys
import logging
import asyncio
from typing import Dict, List
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import UserAlreadyParticipant, UserNotParticipant

# This is the bridge library you need.
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioLavalink, AudioPiped, GroupCall

# Import the automated Lavalink server manager
from lavalink_setup import LavalinkManager

# Import the Python client for Lavalink
import lavalink

# -------------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------------
# Load config from environment variables
API_ID = os.environ.get("37862320")
API_HASH = os.environ.get("cdb4a59a76fae6bd8fa42e77455f8697")
BOT_TOKEN = os.environ.get("8341511264:AAFjNIOYE5NbABPloFbz-r989l2ySRUs988")
SESSION_STRING = os.environ.get("BQJBu7AAhhG6MmNUFoqJukQOFZDPl5I4QrcapymDjzK5XNYTqaofTEqI5v12xgg0_xkARp-oRG0bXkUhmRB5ziTmjbDSh4I0ty2tGheoT6-mEzOYIsUKMXRuNfAb-Li9eAvlokTfxwCVa9HTBnOD3cPe_plNAUpRuyk5FtUmdeV5Wu_lWcE5cRECGnW0SHO24GiyHoK8jK6BAVL25rVnwLqktC1O2IZn3cam0hCs2ZqSF_B_4Z-8cuREGMaO8IrRnhOl3adW5sUzlOz14FmrHlGeyAL_s8Cb0tgFbST6EAFW25MWVv_0FG_cKbAxWCoR7u9uG4AhX6NrG3g3Z3ZB53N06rEL8AAAAAHQ8OAyAA") # Userbot session string

# Check if all configs are set
if not all([API_ID, API_HASH, BOT_TOKEN, SESSION_STRING]):
    print("Error: API_ID, API_HASH, BOT_TOKEN, and SESSION_STRING env variables must be set.")
    sys.exit(1)

# Convert API_ID to integer
try:
    API_ID = int(API_ID)
except ValueError:
    print("Error: API_ID must be an integer.")
    sys.exit(1)

LAVALINK_HOST = "127.0.0.1"
LAVALINK_PORT = 2333
LAVALINK_PASS = "youshallnotpass"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Bot & Client Initialization
# -------------------------------------------------------------------------------

# Pyrogram Bot Client (Handles commands)
bot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# Pyrogram User Client (Handles audio streaming via PyTgCalls)
# We use the Session String for this.
user_app = Client(
    "MusicUser",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

# PyTgCalls Client (The bridge)
pytgcalls = PyTgCalls(user_app)

# Lavalink Client (Handles searching and track loading)
lavalink_client = None

# In-memory queue
# { chat_id: [track, track, ...] }
queue: Dict[int, List[lavalink.Track]] = {}
current_track: Dict[int, lavalink.Track] = {}

# -------------------------------------------------------------------------------
# Lavalink Event Handlers
# -------------------------------------------------------------------------------

# This event is triggered when a track starts playing
@pytgcalls.on_stream_start()
async def on_stream_start(client: GroupCall, track):
    chat_id = track.chat_id
    if chat_id in current_track:
        song = current_track[chat_id]
        await bot.send_message(
            chat_id,
            f"▶️ **Now Playing:**\n\n[{song.title}]({song.uri})\nby {song.author}"
        )

# This event is crucial. It's triggered when a track finishes.
@pytgcalls.on_stream_end()
async def on_stream_end(client: GroupCall, track):
    chat_id = track.chat_id
    current_track.pop(chat_id, None)
    
    if chat_id in queue and queue[chat_id]:
        # Get next song from queue
        next_song = queue[chat_id].pop(0)
        current_track[chat_id] = next_song
        
        # Play the next song
        try:
            await pytgcalls.change_stream(
                chat_id,
                AudioLavalink(
                    next_song.track,
                    user_id=next_song.requester
                )
            )
        except Exception as e:
            logger.error(f"Error playing next song in {chat_id}: {e}")
            await bot.send_message(chat_id, f"Error playing next song: {e}")
    else:
        # Queue is empty, leave the call
        try:
            await pytgcalls.leave_group_call(chat_id)
            await bot.send_message(chat_id, "⏹ Queue finished, leaving voice chat.")
        except Exception as e:
            logger.error(f"Error leaving group call in {chat_id}: {e}")

# -------------------------------------------------------------------------------
# Bot Command Handlers
# -------------------------------------------------------------------------------

@bot.on_message(filters.command("start") & filters.private)
async def start_command(_, message: Message):
    await message.reply(
        "Hi! I'm a Lavalink music bot.\n"
        "Add me to a group chat and I'll play music.\n\n"
        "**Commands:**\n"
        " - /play [query] - Play a song or add to queue\n"
        " - /stop - Stop playback and leave\n"
        " - /skip - Skip to the next song\n"
        " - /queue - Show the current queue"
    )

@bot.on_message(filters.command("play") & filters.group)
async def play_command(_, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = " ".join(message.command[1:])

    if not query:
        return await message.reply("Please provide a song name or YouTube URL.")
        
    # Search for the track on Lavalink
    try:
        results = await lavalink_client.get_tracks(f"ytsearch:{query}")
    except Exception as e:
        logger.error(f"Lavalink search error: {e}")
        return await message.reply(f"Error searching for track: {e}")

    if not results or not results.tracks:
        return await message.reply("No tracks found.")

    # Get the first track from the search
    track = results.tracks[0]
    track.requester = user_id # Store who requested the song

    # Check if currently playing
    is_playing = chat_id in current_track

    if is_playing:
        # Add to queue
        if chat_id not in queue:
            queue[chat_id] = []
        queue[chat_id].append(track)
        await message.reply(f"✅ **Added to queue:**\n[{track.title}]({track.uri})")
    else:
        # Play immediately
        current_track[chat_id] = track
        try:
            # Join the voice chat
            await pytgcalls.join_group_call(
                chat_id,
                AudioLavalink(
                    track.track,
                    user_id=user_id
                ),
                stream_type=GroupCall.STREAM_TYPE_MUSIC,
            )
            # The 'on_stream_start' event will handle the "Now Playing" message
        except UserAlreadyParticipant:
            # Already in the call, just change the stream
            await pytgcalls.change_stream(
                chat_id,
                AudioLavalink(
                    track.track,
                    user_id=user_id
                )
            )
        except UserNotParticipant:
            await message.reply("I can't join. Please check my userbot's permissions.")
        except Exception as e:
            logger.error(f"Error joining call in {chat_id}: {e}")
            await message.reply(f"Error: {e}")
            current_track.pop(chat_id, None)

@bot.on_message(filters.command("skip") & filters.group)
async def skip_command(_, message: Message):
    chat_id = message.chat.id

    if chat_id not in current_track:
        return await message.reply("Not playing anything.")

    if not queue.get(chat_id):
        await message.reply("Queue is empty, stopping playback.")
        await pytgcalls.leave_group_call(chat_id)
        current_track.pop(chat_id, None)
        return

    # Get next song
    next_song = queue[chat_id].pop(0)
    current_track[chat_id] = next_song
    
    try:
        await pytgcalls.change_stream(
            chat_id,
            AudioLavalink(
                next_song.track,
                user_id=next_song.requester
            )
        )
        await message.reply("⏭ **Skipped!**")
        # 'on_stream_start' will announce the new song
    except Exception as e:
        logger.error(f"Error skipping in {chat_id}: {e}")
        await message.reply(f"Error skipping: {e}")


@bot.on_message(filters.command("stop") & filters.group)
async def stop_command(_, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in current_track:
        return await message.reply("Not playing anything.")
        
    try:
        await pytgcalls.leave_group_call(chat_id)
        current_track.pop(chat_id, None)
        queue.pop(chat_id, None)
        await message.reply("⏹ **Stopped playback** and left voice chat.")
    except Exception as e:
        logger.error(f"Error stopping in {chat_id}: {e}")
        await message.reply(f"Error stopping: {e}")

@bot.on_message(filters.command("queue") & filters.group)
async def queue_command(_, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in current_track:
        return await message.reply("Not playing anything.")

    msg = "**Current Queue:**\n\n"
    
    # Show current track
    song = current_track[chat_id]
    msg += f"**Now Playing:**\n[{song.title}]({song.uri})\n\n"

    # Show upcoming tracks
    if queue.get(chat_id):
        msg += "**Up Next:**\n"
        for i, track in enumerate(queue[chat_id][:10], start=1):
            msg += f"`{i}.` [{track.title}]({track.uri})\n"
        
        if len(queue[chat_id]) > 10:
            msg += f"\n...and {len(queue[chat_id]) - 10} more."
            
    else:
        msg += "Queue is empty."

    await message.reply(msg, disable_web_page_preview=True)

# -------------------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------------------

async def main():
    global lavalink_client
    
    lavalink_manager = None
    try:
        # 1. Start the automated Lavalink server
        lavalink_manager = LavalinkManager()
        await lavalink_manager.start()
        
        # 2. Start the Pyrogram clients (Bot + User)
        logger.info("Starting Pyrogram clients...")
        await bot.start()
        await user_app.start()
        
        # 3. Start PyTgCalls
        logger.info("Starting PyTgCalls...")
        await pytgcalls.start()

        # 4. Get the userbot's ID (needed for Lavalink client)
        userbot_me = await user_app.get_me()
        
        # 5. Initialize and connect the Lavalink client
        logger.info("Initializing Lavalink client...")
        lavalink_client = lavalink.Client(user_id=userbot_me.id)
        lavalink_client.add_node(
            host=LAVALINK_HOST,
            port=LAVALINK_PORT,
            password=LAVALINK_PASS,
            region="us-central" # Region is arbitrary
        )
        
        logger.info("Bot is fully operational!")
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
    finally:
        # 6. Stop everything gracefully
        logger.info("Stopping clients...")
        if bot.is_connected:
            await bot.stop()
        if user_app.is_connected:
            await user_app.stop()
        if lavalink_manager:
            lavalink_manager.stop()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
