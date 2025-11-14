import os
import sys
import logging
import asyncio
from typing import Dict, List
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import UserAlreadyParticipant, UserNotParticipant

# --- NEW STABLE VOICE CALL IMPORTS ---
# This library is a more stable wrapper for streaming audio via Pyrogram.
from pyrogram_voice_chat import GroupCallFactory, Stream
from pyrogram_voice_chat.stream import AudioQuality

# --- NEW MUSIC SOURCING LIBRARY ---
import yt_dlp
import json

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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global instances (simplified)
bot = None
user_app = None
group_call_factory = None
# Dictionary to store the GroupCall instance for each chat
group_calls: Dict[int, 'GroupCall'] = {}

# In-memory queue storage
# The 'Track' object is now a simple dict containing URL and title
# { chat_id: [track_dict, track_dict, ...] }
queue: Dict[int, List[Dict]] = {}

# -------------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------------

def extract_audio_info(query: str) -> Dict | None:
    """Uses yt-dlp to extract the best streaming URL and metadata."""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'extract_flat': 'in_playlist',
        'force_ipv4': True,
        'cachedir': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                # Get the first result from a search
                info = info['entries'][0]
            
            # Find the best quality stream URL
            audio_url = info.get('url') # yt-dlp finds the direct stream URL
            
            if not audio_url:
                # Fallback to finding a suitable stream format
                for fmt in info.get('formats', []):
                    if fmt.get('acodec') != 'none' and fmt.get('ext') in ['m4a', 'mp3', 'webm', 'ogg']:
                        audio_url = fmt.get('url')
                        break
            
            if not audio_url:
                 # If we still don't have a URL, it's a failure
                 return None

            return {
                "title": info.get('title', 'Unknown Title'),
                "url": audio_url,
                "duration": info.get('duration'),
                "webpage_url": info.get('webpage_url')
            }

    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {e}")
        return None

async def play_next_in_queue(chat_id: int):
    """Handles playing the next song or leaving the call if the queue is empty."""
    if chat_id in queue and queue[chat_id]:
        next_song = queue[chat_id].pop(0)
        
        # Stream needs to be re-created for the new track
        new_stream = Stream(
            next_song['url'],
            quality=AudioQuality.HIGH,
            title=next_song['title']
        )
        
        try:
            # Change stream using the new library's method
            await group_calls[chat_id].change_stream(new_stream)
            await bot.send_message(
                chat_id,
                f"▶️ **Now Playing:**\n\n[{next_song['title']}]({next_song['webpage_url']})"
            )
        except Exception as e:
            logger.error(f"Error playing next song in {chat_id}: {e}")
            await bot.send_message(chat_id, f"Error playing next song: {e}")
            # If playback fails, try the next song recursively
            await play_next_in_queue(chat_id) 

    else:
        # Queue is empty, leave the call
        if chat_id in group_calls:
            try:
                await group_calls[chat_id].stop()
                group_calls.pop(chat_id)
                await bot.send_message(chat_id, "⏹ Queue finished, leaving voice chat.")
            except Exception as e:
                logger.error(f"Error leaving group call in {chat_id}: {e}")

# -------------------------------------------------------------------------------
# Bot Command Handlers
# -------------------------------------------------------------------------------

@bot.on_message(filters.command("play") & filters.group)
async def play_command(_, message: Message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:])

    if not query:
        return await message.reply("Please provide a song name or YouTube URL.")
        
    m = await message.reply("🔎 Searching and processing audio stream...")
    
    # 1. Search and extract track info
    track = await asyncio.get_event_loop().run_in_executor(
        None, # Use default thread pool for blocking I/O (yt-dlp)
        extract_audio_info,
        query
    )

    if not track:
        await m.edit("❌ Error: Could not find or process the audio stream.")
        return

    # 2. Check if currently playing
    is_playing = chat_id in group_calls and group_calls[chat_id].is_connected

    if is_playing:
        # Add to queue
        if chat_id not in queue:
            queue[chat_id] = []
        queue[chat_id].append(track)
        await m.edit(f"✅ **Added to queue:**\n[{track['title']}]({track['webpage_url']})")
    else:
        # Play immediately
        
        # 3. Create a Stream object from the extracted URL
        audio_stream = Stream(
            track['url'],
            quality=AudioQuality.HIGH,
            title=track['title'],
            # Set the callback for when the stream ends (Crucial!)
            on_finished=lambda: asyncio.create_task(play_next_in_queue(chat_id))
        )

        try:
            # 4. Join the voice chat
            group_call = group_call_factory.get_group_call()
            await group_call.start(chat_id)
            await group_call.join_group_call(audio_stream)
            
            group_calls[chat_id] = group_call
            
            await m.edit(f"▶️ **Now Playing:**\n\n[{track['title']}]({track['webpage_url']})")

        except UserAlreadyParticipant:
            # Already in the call, just change the stream (this is highly unlikely with this library's flow)
            await group_calls[chat_id].change_stream(audio_stream)
            await m.edit(f"▶️ **Now Playing:**\n\n[{track['title']}]({track['webpage_url']})")

        except UserNotParticipant:
            await m.edit("❌ I can't join. Please check my userbot's permissions.")
        except Exception as e:
            logger.error(f"Error joining call in {chat_id}: {e}")
            await m.edit(f"❌ Error: {e}")
            if chat_id in group_calls:
                await group_calls[chat_id].stop()
                group_calls.pop(chat_id)

@bot.on_message(filters.command("skip") & filters.group)
async def skip_command(_, message: Message):
    chat_id = message.chat.id

    if chat_id not in group_calls or not group_calls[chat_id].is_connected:
        return await message.reply("Not playing anything.")
        
    await message.reply("⏭ **Skipping track...**")
    
    # Trigger the next song immediately by stopping the current stream
    # The 'on_finished' callback in the stream handles playing the next song.
    try:
        await group_calls[chat_id].stop_stream()
    except Exception as e:
        logger.error(f"Error during skip: {e}")
        await play_next_in_queue(chat_id)


@bot.on_message(filters.command("stop") & filters.group)
async def stop_command(_, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in group_calls or not group_calls[chat_id].is_connected:
        return await message.reply("Not playing anything.")
        
    try:
        await group_calls[chat_id].stop()
        group_calls.pop(chat_id)
        queue.pop(chat_id, None)
        await message.reply("⏹ **Stopped playback** and left voice chat.")
    except Exception as e:
        logger.error(f"Error stopping in {chat_id}: {e}")
        await message.reply(f"Error stopping: {e}")

@bot.on_message(filters.command("queue") & filters.group)
async def queue_command(_, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in group_calls or not group_calls[chat_id].is_connected:
        return await message.reply("Not playing anything.")

    msg = "**Current Queue:**\n\n"
    
    # Since the current song title is attached to the stream object
    try:
        current_title = group_calls[chat_id].active_stream.title
        current_url = group_calls[chat_id].active_stream.url
        msg += f"**Now Playing:**\n[{current_title}](https://www.youtube.com/watch?v={current_url.split('/')[4].split('?')[0]})\n\n" # Crude way to get YouTube link
    except:
        msg += "**Now Playing:** *Error retrieving current track info.*\n\n"
        
    # Show upcoming tracks
    if queue.get(chat_id):
        msg += "**Up Next:**\n"
        for i, track in enumerate(queue[chat_id][:10], start=1):
            # Using the stored webpage_url as the link
            msg += f"`{i}.` [{track['title']}]({track['webpage_url']})\n"
        
        if len(queue[chat_id]) > 10:
            msg += f"\n...and {len(queue[chat_id]) - 10} more."
            
    else:
        msg += "Queue is empty."

    await message.reply(msg, disable_web_page_preview=True)

# -------------------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------------------

async def main():
    global bot, user_app, group_call_factory
    
    try:
        # 1. Start the Pyrogram clients (Bot + User)
        logger.info("Starting Pyrogram clients...")
        bot = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        user_app = Client("MusicUser", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
        
        await bot.start()
        await user_app.start()

        # 2. Initialize the Group Call Factory
        group_call_factory = GroupCallFactory(user_app, 'telegram_music_bot.session')
        
        logger.info("Bot is fully operational with stable streaming!")
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
    finally:
        # 3. Stop everything gracefully
        logger.info("Stopping clients...")
        if bot and bot.is_connected:
            await bot.stop()
        if user_app and user_app.is_connected:
            await user_app.stop()
        # Clean up any active calls
        for call in group_calls.values():
            if call.is_connected:
                await call.stop()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
