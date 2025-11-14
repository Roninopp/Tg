import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode
import yt_dlp
import aiohttp
import aiofiles
import os
from collections import deque
from typing import Dict, Optional
import re
import time

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = "37862320"
API_HASH = "cdb4a59a76fae6bd8fa42e77455f8697"
BOT_TOKEN = "8341511264:AAFjNIOYE5NbABPloFbz-r989l2ySRUs988"
USER_SESSION = "BQJBu7AAhhG6MmNUFoqJukQOFZDPl5I4QrcapymDjzK5XNYTqaofTEqI5v12xgg0_xkARp-oRG0bXkUhmRB5ziTmjbDSh4I0ty2tGheoT6-mEzOYIsUKMXRuNfAb-Li9eAvlokTfxwCVa9HTBnOD3cPe_plNAUpRuyk5FtUmdeV5Wu_lWcE5cRECGnW0SHO24GiyHoK8jK6BAVL25rVnwLqktC1O2IZn3cam0hCs2ZqSF_B_4Z-8cuREGMaO8IrRnhOl3adW5sUzlOz14FmrHlGeyAL_s8Cb0tgFbST6EAFW25MWVv_0FG_cKbAxWCoR7u9uG4AhX6NrG3g3Z3ZB53N06rEL8AAAAAHQ8OAyAA"

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

# FIXED: Enhanced yt-dlp options to avoid bot detection
ydl_opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False,
    'extract_flat': False,
    'age_limit': None,
    'geo_bypass': True,
    'no_color': True,
    # Anti-bot detection headers
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
    },
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Fallback yt-dlp options for stubborn videos
ydl_opts_fallback = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'extract_flat': 'in_playlist',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'skip': ['dash', 'hls']
        }
    },
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

async def safe_send_message(chat_id: int, text: str, reply_to_message_id: int = None) -> Optional[Message]:
    """FIXED: Send message without entity bounds errors - plain text only"""
    try:
        # Remove all markdown/html formatting to avoid entity errors
        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
        
        return await bot.send_message(
            chat_id=chat_id,
            text=clean_text,
            reply_to_message_id=reply_to_message_id,
            parse_mode=None  # Disable all parsing
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # Try one more time with even simpler text
        try:
            simple_text = ''.join(c for c in clean_text if c.isprintable() or c in ['\n', '\t'])
            return await bot.send_message(
                chat_id=chat_id,
                text=simple_text,
                reply_to_message_id=reply_to_message_id
            )
        except:
            return None

async def safe_edit_message(message: Message, text: str) -> bool:
    """FIXED: Edit message without entity bounds errors"""
    try:
        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
        await message.edit_text(clean_text, parse_mode=None)
        return True
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return False

async def download_audio(url: str, use_fallback: bool = False) -> Optional[dict]:
    """FIXED: Download audio with bot detection bypass and fallback methods"""
    try:
        options = ydl_opts_fallback if use_fallback else ydl_opts
        
        with yt_dlp.YoutubeDL(options) as ydl:
            # Extract info first
            logger.info(f"Extracting info from: {url}")
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("No info extracted")
                return None
            
            # Download the audio
            logger.info(f"Downloading: {info.get('title', 'Unknown')}")
            info = ydl.extract_info(url, download=True)
            
            # Get the downloaded file path
            file_path = ydl.prepare_filename(info)
            # Change extension to mp3
            base_path = file_path.rsplit('.', 1)[0]
            mp3_path = base_path + '.mp3'
            
            # Wait for file to be ready
            max_wait = 30
            wait_count = 0
            while not os.path.exists(mp3_path) and wait_count < max_wait:
                await asyncio.sleep(1)
                wait_count += 1
                # Check for other audio formats
                for ext in ['.m4a', '.webm', '.opus', '.ogg']:
                    alt_path = base_path + ext
                    if os.path.exists(alt_path):
                        mp3_path = alt_path
                        break
            
            if not os.path.exists(mp3_path):
                logger.error(f"Downloaded file not found: {mp3_path}")
                return None
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': mp3_path,
                'url': url,
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown')
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        logger.error(f"yt-dlp download error: {e}")
        
        # Check for specific bot detection errors
        if 'sign in' in error_msg or 'bot' in error_msg or 'captcha' in error_msg:
            logger.warning("Bot detection encountered, trying fallback method...")
            if not use_fallback:
                await asyncio.sleep(2)
                return await download_audio(url, use_fallback=True)
        
        return None
        
    except yt_dlp.utils.ExtractorError as e:
        logger.error(f"yt-dlp extractor error: {e}")
        if not use_fallback:
            logger.info("Trying fallback extraction method...")
            await asyncio.sleep(2)
            return await download_audio(url, use_fallback=True)
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error downloading audio: {e}")
        return None

async def search_youtube(query: str) -> Optional[str]:
    """FIXED: Search YouTube with enhanced bot detection bypass"""
    try:
        search_opts = {
            'format': 'bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'extract_flat': True,
            'geo_bypass': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }
        
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            logger.info(f"Searching YouTube for: {query}")
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if info and 'entries' in info and info['entries']:
                video_id = info['entries'][0].get('id')
                if video_id:
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
            stream_audio=None,
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
        if not music_queue.active_calls.get(chat_id):
            await join_voice_chat(chat_id)
        
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
        await leave_voice_chat(chat_id)
        return None
    
    music_queue.current[chat_id] = track
    success = await play_audio(chat_id, track['file_path'])
    
    if success:
        return track
    else:
        return await play_next(chat_id)

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Start command handler"""
    text = (
        "🎵 Welcome to Music Bot!\n\n"
        "Available Commands:\n"
        "/play <song name or URL> - Play a song\n"
        "/stop - Stop playing and clear queue\n"
        "/skip - Skip current song\n"
        "/queue - Show current queue\n"
        "/pause - Pause playback\n"
        "/resume - Resume playback\n"
        "/help - Show this message"
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Help command handler"""
    text = (
        "🎵 Music Bot Help\n\n"
        "Commands:\n"
        "/play - Play music from YouTube (URL or search query)\n"
        "/stop - Stop current playback and clear queue\n"
        "/skip - Skip to next song in queue\n"
        "/queue - Display current queue\n"
        "/pause - Pause current song\n"
        "/resume - Resume paused song\n\n"
        "Usage Examples:\n"
        "/play Never Gonna Give You Up\n"
        "/play https://youtube.com/watch?v=...\n\n"
        "Note: Bot must be admin with voice chat permissions!"
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """FIXED: Play command with proper error handling"""
    try:
        if len(message.command) < 2:
            await safe_send_message(
                message.chat.id,
                "❌ Please provide a song name or URL!\n\nUsage: /play <song name or URL>",
                message.id
            )
            return
        
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        status_msg = await safe_send_message(chat_id, "🔍 Searching and downloading...", message.id)
        if not status_msg:
            return
        
        # Check if URL or search query
        url_pattern = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/')
        if url_pattern.match(query):
            url = query
        else:
            await safe_edit_message(status_msg, "🔍 Searching YouTube...")
            url = await search_youtube(query)
            
            if not url:
                await safe_edit_message(status_msg, "❌ No results found! Try a different search query.")
                return
        
        # Download audio with retry logic
        await safe_edit_message(status_msg, "⬇️ Downloading audio... This may take a moment.")
        
        track_info = await download_audio(url)
        
        # If first attempt failed, try fallback
        if not track_info:
            await safe_edit_message(status_msg, "⬇️ Retrying with alternative method...")
            await asyncio.sleep(2)
            track_info = await download_audio(url, use_fallback=True)
        
        if not track_info:
            await safe_edit_message(
                status_msg,
                "❌ Failed to download audio!\n\n"
                "Possible reasons:\n"
                "- Video is age-restricted\n"
                "- Video is not available\n"
                "- Network issue\n\n"
                "Try a different song or URL."
            )
            return
        
        # Add to queue
        music_queue.add(chat_id, track_info)
        
        # If nothing is playing, start playback
        if chat_id not in music_queue.current or not music_queue.current.get(chat_id):
            await safe_edit_message(status_msg, "🎵 Starting playback...")
            track = await play_next(chat_id)
            
            if track:
                duration_str = f"{track['duration'] // 60}:{track['duration'] % 60:02d}"
                text = (
                    f"▶️ Now Playing:\n"
                    f"🎵 {track['title']}\n"
                    f"👤 {track['uploader']}\n"
                    f"⏱ Duration: {duration_str}"
                )
                await safe_edit_message(status_msg, text)
            else:
                await safe_edit_message(status_msg, "❌ Failed to start playback! Check bot permissions.")
        else:
            queue_position = len(music_queue.get_queue(chat_id))
            text = (
                f"✅ Added to queue:\n"
                f"🎵 {track_info['title']}\n"
                f"📊 Position: {queue_position}"
            )
            await safe_edit_message(status_msg, text)
            
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        error_text = f"❌ An error occurred: {str(e)[:100]}"
        await safe_send_message(message.chat.id, error_text, message.id)

@bot.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    """Stop command handler"""
    try:
        chat_id = message.chat.id
        
        music_queue.clear(chat_id)
        await leave_voice_chat(chat_id)
        
        await safe_send_message(chat_id, "⏹️ Stopped playback and cleared queue!", message.id)
        
        if chat_id in music_queue.current:
            file_path = music_queue.current[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
                
    except Exception as e:
        logger.error(f"Error in stop command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

@bot.on_message(filters.command("skip"))
async def skip_command(client: Client, message: Message):
    """Skip command handler"""
    try:
        chat_id = message.chat.id
        
        if chat_id in music_queue.current:
            file_path = music_queue.current[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        track = await play_next(chat_id)
        
        if track:
            text = (
                f"⏭️ Skipped! Now Playing:\n"
                f"🎵 {track['title']}\n"
                f"👤 {track['uploader']}"
            )
            await safe_send_message(chat_id, text, message.id)
        else:
            await safe_send_message(chat_id, "⏹️ No more songs in queue!", message.id)
            
    except Exception as e:
        logger.error(f"Error in skip command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

@bot.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    """Queue command handler"""
    try:
        chat_id = message.chat.id
        current = music_queue.current.get(chat_id)
        queue = music_queue.get_queue(chat_id)
        
        if not current and not queue:
            await safe_send_message(chat_id, "📭 Queue is empty!", message.id)
            return
        
        response = "📃 Current Queue:\n\n"
        
        if current:
            response += f"▶️ Now Playing:\n🎵 {current['title']}\n\n"
        
        if queue:
            response += "Up Next:\n"
            for i, track in enumerate(queue[:10], 1):  # Limit to 10 to avoid message too long
                response += f"{i}. {track['title']}\n"
            
            if len(queue) > 10:
                response += f"\n...and {len(queue) - 10} more"
        
        await safe_send_message(chat_id, response, message.id)
        
    except Exception as e:
        logger.error(f"Error in queue command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

@bot.on_message(filters.command("pause"))
async def pause_command(client: Client, message: Message):
    """Pause command handler"""
    try:
        chat_id = message.chat.id
        await userbot.pause_stream_audio(chat_id)
        await safe_send_message(chat_id, "⏸️ Paused playback!", message.id)
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

@bot.on_message(filters.command("resume"))
async def resume_command(client: Client, message: Message):
    """Resume command handler"""
    try:
        chat_id = message.chat.id
        await userbot.resume_stream_audio(chat_id)
        await safe_send_message(chat_id, "▶️ Resumed playback!", message.id)
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

async def main():
    """Main function to start the bot"""
    os.makedirs("downloads", exist_ok=True)
    
    await bot.start()
    await userbot.start()
    
    logger.info("Bot and Userbot started successfully!")
    print("🎵 Music Bot is running...")
    print("✅ Bot detection bypass enabled")
    print("✅ Enhanced error handling active")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        bot.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        if os.path.exists("downloads"):
            for file in os.listdir("downloads"):
                try:
                    os.remove(os.path.join("downloads", file))
                except:
                    pass
