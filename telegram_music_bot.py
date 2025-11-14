import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import yt_dlp
import aiohttp
import aiofiles
import os
from collections import deque
from typing import Dict, Optional
import re

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = "37862320"  # Get from my.telegram.org
API_HASH = "cdb4a59a76fae6bd8fa42e77455f8697"
BOT_TOKEN = "8341511264:AAFjNIOYE5NbABPloFbz-r989l2ySRUs988"  # Get from @BotFather

# Userbot credentials for voice chat
USER_SESSION = "BQJBu7AAhhG6MmNUFoqJukQOFZDPl5I4QrcapymDjzK5XNYTqaofTEqI5v12xgg0_xkARp-oRG0bXkUhmRB5ziTmjbDSh4I0ty2tGheoT6-mEzOYIsUKMXRuNfAb-Li9eAvlokTfxwCVa9HTBnOD3cPe_plNAUpRuyk5FtUmdeV5Wu_lWcE5cRECGnW0SHO24GiyHoK8jK6BAVL25rVnwLqktC1O2IZn3cam0hCs2ZqSF_B_4Z-8cuREGMaO8IrRnhOl3adW5sUzlOz14FmrHlGeyAL_s8Cb0tgFbST6EAFW25MWVv_0FG_cKbAxWCoR7u9uG4AhX6NrG3g3Z3ZB53N06rEL8AAAAAHQ8OAyAA"  # Generate using generate_session.py

# Initialize clients
bot = Client(
    "music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=USER_SESSION
)

# Global state management
class MusicQueue:
    def __init__(self):
        self.queues: Dict[int, deque] = {}
        self.current: Dict[int, dict] = {}
        self.active_calls: Dict[int, bool] = {}
    
    def add(self, chat_id: int, track: dict):
        if chat_id not in self.queues:
            self.queues[chat_id] = deque()
        self.queues[chat_id].append(track)
    
    def get_next(self, chat_id: int) -> Optional[dict]:
        if chat_id in self.queues and self.queues[chat_id]:
            return self.queues[chat_id].popleft()
        return None
    
    def clear(self, chat_id: int):
        if chat_id in self.queues:
            self.queues[chat_id].clear()
        if chat_id in self.current:
            del self.current[chat_id]
    
    def get_queue(self, chat_id: int) -> list:
        if chat_id in self.queues:
            return list(self.queues[chat_id])
        return []

music_queue = MusicQueue()

# YouTube downloader configuration
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

async def download_audio(url: str) -> Optional[dict]:
    """Download audio from YouTube URL"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the downloaded file path
            file_path = ydl.prepare_filename(info)
            # Change extension to mp3
            file_path = file_path.rsplit('.', 1)[0] + '.mp3'
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'url': url,
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown')
            }
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return None

async def search_youtube(query: str) -> Optional[str]:
    """Search YouTube and return first result URL"""
    try:
        ydl_opts_search = {
            'format': 'bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and 'entries' in info and info['entries']:
                video_id = info['entries'][0]['id']
                return f"https://www.youtube.com/watch?v={video_id}"
        return None
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        return None

async def join_voice_chat(chat_id: int):
    """Join voice chat using Pyrogram native methods"""
    try:
        await userbot.join_group_call(
            chat_id=chat_id,
            stream_audio=None,  # Will be set when playing
        )
        music_queue.active_calls[chat_id] = True
        logger.info(f"Joined voice chat in {chat_id}")
        return True
    except FloodWait as e:
        logger.warning(f"FloodWait: sleeping for {e.value} seconds")
        await asyncio.sleep(e.value)
        return await join_voice_chat(chat_id)
    except Exception as e:
        logger.error(f"Error joining voice chat: {e}")
        return False

async def leave_voice_chat(chat_id: int):
    """Leave voice chat"""
    try:
        await userbot.leave_group_call(chat_id)
        music_queue.active_calls[chat_id] = False
        logger.info(f"Left voice chat in {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error leaving voice chat: {e}")
        return False

async def play_audio(chat_id: int, file_path: str):
    """Stream audio to voice chat"""
    try:
        # Check if already in call, if not join
        if not music_queue.active_calls.get(chat_id):
            await join_voice_chat(chat_id)
        
        # Change audio stream
        await userbot.change_stream_audio(
            chat_id=chat_id,
            file_path=file_path
        )
        logger.info(f"Playing audio in {chat_id}: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        return False

async def play_next(chat_id: int):
    """Play next track in queue"""
    track = music_queue.get_next(chat_id)
    if not track:
        # Queue is empty, leave voice chat
        await leave_voice_chat(chat_id)
        return None
    
    music_queue.current[chat_id] = track
    success = await play_audio(chat_id, track['file_path'])
    
    if success:
        return track
    else:
        # Try next track if current failed
        return await play_next(chat_id)

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Start command handler"""
    await message.reply_text(
        "🎵 **Welcome to Music Bot!**\n\n"
        "**Available Commands:**\n"
        "/play <song name or URL> - Play a song\n"
        "/stop - Stop playing and clear queue\n"
        "/skip - Skip current song\n"
        "/queue - Show current queue\n"
        "/pause - Pause playback\n"
        "/resume - Resume playback\n"
        "/help - Show this message"
    )

@bot.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Help command handler"""
    await message.reply_text(
        "🎵 **Music Bot Help**\n\n"
        "**Commands:**\n"
        "• `/play` - Play music from YouTube (URL or search query)\n"
        "• `/stop` - Stop current playback and clear queue\n"
        "• `/skip` - Skip to next song in queue\n"
        "• `/queue` - Display current queue\n"
        "• `/pause` - Pause current song\n"
        "• `/resume` - Resume paused song\n\n"
        "**Usage Examples:**\n"
        "`/play Never Gonna Give You Up`\n"
        "`/play https://youtube.com/watch?v=...`\n\n"
        "**Note:** Bot must be admin with voice chat permissions!"
    )

@bot.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """Play command handler"""
    try:
        if len(message.command) < 2:
            await message.reply_text("❌ Please provide a song name or URL!\n\nUsage: `/play <song name or URL>`")
            return
        
        # Get query
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        # Send processing message
        status_msg = await message.reply_text("🔍 Searching and downloading...")
        
        # Check if URL or search query
        url_pattern = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/')
        if url_pattern.match(query):
            url = query
        else:
            url = await search_youtube(query)
            if not url:
                await status_msg.edit_text("❌ No results found!")
                return
        
        # Download audio
        await status_msg.edit_text("⬇️ Downloading audio...")
        track_info = await download_audio(url)
        
        if not track_info:
            await status_msg.edit_text("❌ Failed to download audio!")
            return
        
        # Add to queue
        music_queue.add(chat_id, track_info)
        
        # If nothing is playing, start playback
        if chat_id not in music_queue.current or not music_queue.current.get(chat_id):
            await status_msg.edit_text("🎵 Starting playback...")
            track = await play_next(chat_id)
            if track:
                await status_msg.edit_text(
                    f"▶️ **Now Playing:**\n"
                    f"🎵 {track['title']}\n"
                    f"👤 {track['uploader']}\n"
                    f"⏱ Duration: {track['duration'] // 60}:{track['duration'] % 60:02d}"
                )
            else:
                await status_msg.edit_text("❌ Failed to start playback!")
        else:
            # Added to queue
            queue_position = len(music_queue.get_queue(chat_id))
            await status_msg.edit_text(
                f"✅ **Added to queue:**\n"
                f"🎵 {track_info['title']}\n"
                f"📊 Position: {queue_position}"
            )
            
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")

@bot.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    """Stop command handler"""
    try:
        chat_id = message.chat.id
        
        # Clear queue and leave voice chat
        music_queue.clear(chat_id)
        await leave_voice_chat(chat_id)
        
        await message.reply_text("⏹️ Stopped playback and cleared queue!")
        
        # Clean up downloaded files for this chat
        if chat_id in music_queue.current:
            file_path = music_queue.current[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        logger.error(f"Error in stop command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("skip"))
async def skip_command(client: Client, message: Message):
    """Skip command handler"""
    try:
        chat_id = message.chat.id
        
        # Clean up current file
        if chat_id in music_queue.current:
            file_path = music_queue.current[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        
        # Play next track
        track = await play_next(chat_id)
        
        if track:
            await message.reply_text(
                f"⏭️ **Skipped! Now Playing:**\n"
                f"🎵 {track['title']}\n"
                f"👤 {track['uploader']}"
            )
        else:
            await message.reply_text("⏹️ No more songs in queue!")
            
    except Exception as e:
        logger.error(f"Error in skip command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    """Queue command handler"""
    try:
        chat_id = message.chat.id
        
        # Get current and queue
        current = music_queue.current.get(chat_id)
        queue = music_queue.get_queue(chat_id)
        
        if not current and not queue:
            await message.reply_text("📭 Queue is empty!")
            return
        
        response = "📃 **Current Queue:**\n\n"
        
        if current:
            response += f"▶️ **Now Playing:**\n🎵 {current['title']}\n\n"
        
        if queue:
            response += "**Up Next:**\n"
            for i, track in enumerate(queue, 1):
                response += f"{i}. {track['title']}\n"
        
        await message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error in queue command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("pause"))
async def pause_command(client: Client, message: Message):
    """Pause command handler"""
    try:
        chat_id = message.chat.id
        await userbot.pause_stream_audio(chat_id)
        await message.reply_text("⏸️ Paused playback!")
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("resume"))
async def resume_command(client: Client, message: Message):
    """Resume command handler"""
    try:
        chat_id = message.chat.id
        await userbot.resume_stream_audio(chat_id)
        await message.reply_text("▶️ Resumed playback!")
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

async def main():
    """Main function to start the bot"""
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    # Start both clients
    await bot.start()
    await userbot.start()
    
    logger.info("Bot and Userbot started successfully!")
    print("🎵 Music Bot is running...")
    
    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        bot.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Cleanup
        if os.path.exists("downloads"):
            for file in os.listdir("downloads"):
                try:
                    os.remove(os.path.join("downloads", file))
                except:
                    pass
