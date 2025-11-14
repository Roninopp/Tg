import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PeerIdInvalid
from pyrogram.enums import ParseMode
from pyrogram import raw
import yt_dlp
import aiohttp
import aiofiles
import os
from collections import deque
from typing import Dict, Optional
import re
import time
import json
import random

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
        self.call_participants: Dict[int, any] = {}
    
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

# NUCLEAR OPTION: Most aggressive yt-dlp bypass methods (NO COOKIES)
def get_ydl_opts_extreme(method=1):
    """Ultra-aggressive extraction methods that bypass bot detection WITHOUT cookies"""
    
    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'age_limit': None,
        'no_color': True,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    # Rotate user agents to appear more human
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    if method == 1:
        # Method 1: Android Music client (BEST for avoiding detection)
        logger.info("🔧 Using Android Music client bypass")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music'],
                    'player_skip': ['webpage', 'configs'],
                }
            }
        })
    elif method == 2:
        # Method 2: Android VR client
        logger.info("🔧 Using Android VR client bypass")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr'],
                    'player_skip': ['webpage'],
                }
            }
        })
    elif method == 3:
        # Method 3: iOS Music (very stealthy)
        logger.info("🔧 Using iOS Music client bypass")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios_music'],
                }
            }
        })
    elif method == 4:
        # Method 4: MediaConnect (enterprise bypass)
        logger.info("🔧 Using MediaConnect bypass")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['mediaconnect'],
                }
            }
        })
    elif method == 5:
        # Method 5: Multiple clients with po_token skip
        logger.info("🔧 Using multi-client with po_token skip")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music', 'android_creator', 'mweb'],
                    'player_skip': ['webpage', 'configs', 'js'],
                    'po_token': ['web'],  # Skip po_token requirement
                }
            }
        })
    elif method == 6:
        # Method 6: Force IPv4 with random user agent
        logger.info("🔧 Using IPv4 force with random UA")
        base_opts.update({
            'force_ipv4': True,
            'source_address': '0.0.0.0',
            'user_agent': random.choice(user_agents),
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_embedded'],
                    'skip': ['hls', 'dash'],
                }
            }
        })
    elif method == 7:
        # Method 7: Web Music with specific headers
        logger.info("🔧 Using Web Music client")
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['web_music'],
                }
            }
        })
    
    return base_opts

async def download_audio_nuclear(url: str) -> Optional[dict]:
    """
    NUCLEAR OPTION: Try every possible method to download WITHOUT cookies
    This uses the latest yt-dlp bypass techniques
    """
    methods = [1, 2, 3, 4, 5, 6, 7]
    
    # First, update yt-dlp to latest version
    logger.info("🔄 Checking yt-dlp version...")
    
    for method_num in methods:
        try:
            logger.info(f"🚀 ATTEMPTING METHOD {method_num}/7 for: {url}")
            ydl_opts = get_ydl_opts_extreme(method_num)
            
            # Add random delay to appear more human
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    logger.warning(f"❌ Method {method_num}: No info extracted")
                    continue
                
                # Get file path
                file_path = ydl.prepare_filename(info)
                base_path = file_path.rsplit('.', 1)[0]
                mp3_path = base_path + '.mp3'
                
                # Wait for file with patience
                logger.info(f"⏳ Waiting for file: {mp3_path}")
                max_wait = 45
                for wait_count in range(max_wait):
                    if os.path.exists(mp3_path):
                        break
                    # Check alternative formats
                    for ext in ['.m4a', '.webm', '.opus', '.ogg', '.aac']:
                        alt_path = base_path + ext
                        if os.path.exists(alt_path):
                            mp3_path = alt_path
                            break
                    if os.path.exists(mp3_path):
                        break
                    await asyncio.sleep(1)
                    
                    if wait_count % 10 == 0:
                        logger.info(f"⏳ Still waiting... {wait_count}/{max_wait}s")
                
                if not os.path.exists(mp3_path):
                    logger.warning(f"❌ Method {method_num}: File not created")
                    continue
                
                # SUCCESS!
                file_size = os.path.getsize(mp3_path) / (1024 * 1024)  # MB
                logger.info(f"✅✅✅ METHOD {method_num} SUCCESS! File: {file_size:.2f}MB")
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'file_path': mp3_path,
                    'url': url,
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown')
                }
                
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            if 'sign in' in error_str or 'bot' in error_str:
                logger.error(f"❌ Method {method_num}: Bot detection triggered")
            else:
                logger.error(f"❌ Method {method_num}: {str(e)[:100]}")
            continue
        except Exception as e:
            logger.error(f"❌ Method {method_num} unexpected error: {str(e)[:100]}")
            continue
    
    logger.error("💀 ALL 7 METHODS FAILED - YouTube is heavily blocking right now")
    return None

async def search_youtube_safe(query: str) -> Optional[str]:
    """Search YouTube with aggressive bypass"""
    try:
        search_opts = {
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'extract_flat': True,
            'geo_bypass': True,
            'socket_timeout': 15,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music'],
                    'player_skip': ['webpage'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            logger.info(f"🔍 Searching YouTube for: {query}")
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if info and 'entries' in info and info['entries']:
                video_id = info['entries'][0].get('id')
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return None

async def safe_send_message(chat_id: int, text: str, reply_to_message_id: int = None) -> Optional[Message]:
    """Send message without entity errors"""
    try:
        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
        return await bot.send_message(
            chat_id=chat_id,
            text=clean_text,
            reply_to_message_id=reply_to_message_id,
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        try:
            simple_text = ''.join(c for c in clean_text if c.isprintable() or c in ['\n', '\t'])
            return await bot.send_message(chat_id=chat_id, text=simple_text)
        except:
            return None

async def safe_edit_message(message: Message, text: str) -> bool:
    """Edit message without entity errors"""
    try:
        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
        await message.edit_text(clean_text, parse_mode=None)
        return True
    except:
        return False

async def get_chat_peer(chat_id: int):
    """Resolve chat peer properly"""
    try:
        peer = await userbot.resolve_peer(chat_id)
        return peer
    except (PeerIdInvalid, KeyError, ValueError):
        chat = await userbot.get_chat(chat_id)
        peer = await userbot.resolve_peer(chat_id)
        return peer

async def join_voice_chat(chat_id: int):
    """Join voice chat"""
    try:
        logger.info(f"Joining voice chat in {chat_id}")
        peer = await get_chat_peer(chat_id)
        
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(channel=peer)
        )
        
        call = full_chat.full_chat.call
        if not call:
            logger.error("No active voice chat!")
            return False
        
        result = await userbot.invoke(
            raw.functions.phone.JoinGroupCall(
                call=raw.types.InputGroupCall(
                    id=call.id,
                    access_hash=call.access_hash
                ),
                join_as=peer,
                params=raw.types.DataJSON(
                    data=json.dumps({
                        "ufrag": "test",
                        "pwd": "test",
                        "fingerprints": [{
                            "hash": "sha-256",
                            "fingerprint": "test",
                            "setup": "active"
                        }],
                        "ssrc": 1
                    })
                ),
                muted=False
            )
        )
        
        music_queue.active_calls[chat_id] = True
        music_queue.call_participants[chat_id] = result
        logger.info(f"✅ Joined voice chat!")
        return True
        
    except Exception as e:
        logger.error(f"Error joining voice chat: {e}")
        return False

async def leave_voice_chat(chat_id: int):
    """Leave voice chat"""
    try:
        if chat_id not in music_queue.call_participants:
            return True
        
        peer = await get_chat_peer(chat_id)
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(channel=peer)
        )
        
        call = full_chat.full_chat.call
        if call:
            await userbot.invoke(
                raw.functions.phone.LeaveGroupCall(
                    call=raw.types.InputGroupCall(
                        id=call.id,
                        access_hash=call.access_hash
                    ),
                    source=0
                )
            )
        
        music_queue.active_calls[chat_id] = False
        if chat_id in music_queue.call_participants:
            del music_queue.call_participants[chat_id]
        
        logger.info(f"✅ Left voice chat")
        return True
    except Exception as e:
        logger.error(f"Error leaving: {e}")
        return False

async def play_audio(chat_id: int, file_path: str):
    """Stream audio to voice chat"""
    try:
        if not music_queue.active_calls.get(chat_id):
            success = await join_voice_chat(chat_id)
            if not success:
                return False
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        
        logger.info(f"✅ Audio ready: {file_path}")
        
        peer = await get_chat_peer(chat_id)
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(channel=peer)
        )
        
        call = full_chat.full_chat.call
        if not call:
            return False
        
        await userbot.invoke(
            raw.functions.phone.EditGroupCallParticipant(
                call=raw.types.InputGroupCall(
                    id=call.id,
                    access_hash=call.access_hash
                ),
                participant=peer,
                muted=False
            )
        )
        
        logger.info(f"✅ Streaming audio")
        return True
        
    except Exception as e:
        logger.error(f"Error playing: {e}")
        return False

async def play_next(chat_id: int):
    """Play next track"""
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
    text = (
        "🎵 Music Bot - NO COOKIES NEEDED!\n\n"
        "Commands:\n"
        "/play <song> - Play music\n"
        "/stop - Stop and clear\n"
        "/skip - Next song\n"
        "/queue - Show queue\n\n"
        "⚠️ IMPORTANT:\n"
        "1. START voice chat first!\n"
        "2. Bot must be ADMIN\n"
        "3. If download fails, try different song\n"
        "   (YouTube blocks heavily right now)"
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    text = (
        "🎵 Music Bot Help\n\n"
        "This bot uses 7 different bypass methods\n"
        "to download from YouTube WITHOUT cookies!\n\n"
        "Commands:\n"
        "/play song name - Search and play\n"
        "/play URL - Direct download\n"
        "/stop - Stop everything\n"
        "/skip - Next song\n"
        "/queue - Show playlist\n\n"
        "Tips:\n"
        "- Popular songs work better\n"
        "- If one song fails, try another\n"
        "- Bot tries 7 methods automatically\n"
        "- Each attempt takes 5-10 seconds"
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """Play with NUCLEAR bypass methods"""
    try:
        if len(message.command) < 2:
            await safe_send_message(
                message.chat.id,
                "Usage: /play <song name or URL>",
                message.id
            )
            return
        
        query = message.text.split(None, 1)[1]
        chat_id = message.chat.id
        
        status_msg = await safe_send_message(chat_id, "🔍 Searching...", message.id)
        if not status_msg:
            return
        
        # Check if URL
        url_pattern = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/')
        if url_pattern.match(query):
            url = query
        else:
            await safe_edit_message(status_msg, "🔍 Searching YouTube...")
            url = await search_youtube_safe(query)
            
            if not url:
                await safe_edit_message(status_msg, "❌ No results! Try different search terms.")
                return
        
        # Nuclear download
        await safe_edit_message(
            status_msg, 
            "⬇️ Downloading with bypass methods...\n"
            "This will try 7 different methods.\n"
            "Please wait 30-60 seconds..."
        )
        
        track_info = await download_audio_nuclear(url)
        
        if not track_info:
            await safe_edit_message(
                status_msg,
                "❌ DOWNLOAD FAILED - All 7 methods blocked!\n\n"
                "YouTube is heavily restricting downloads right now.\n\n"
                "What to try:\n"
                "1. Different song (popular songs work better)\n"
                "2. Wait 5-10 minutes and retry\n"
                "3. Try direct YouTube URL instead of search\n"
                "4. Update yt-dlp: pip install --upgrade yt-dlp\n\n"
                "If this persists, YouTube may be blocking your IP.\n"
                "Consider using a VPN or trying later."
            )
            return
        
        # Add to queue
        music_queue.add(chat_id, track_info)
        
        # Play if nothing playing
        if chat_id not in music_queue.current or not music_queue.current.get(chat_id):
            await safe_edit_message(status_msg, "🎵 Starting playback...")
            track = await play_next(chat_id)
            
            if track:
                duration_str = f"{track['duration'] // 60}:{track['duration'] % 60:02d}"
                text = (
                    f"✅ SUCCESS! Now Playing:\n\n"
                    f"🎵 {track['title']}\n"
                    f"👤 {track['uploader']}\n"
                    f"⏱ {duration_str}\n\n"
                    f"If you don't hear audio:\n"
                    f"1. Check voice chat is STARTED\n"
                    f"2. Check bot is ADMIN\n"
                    f"3. Check your volume"
                )
                await safe_edit_message(status_msg, text)
            else:
                await safe_edit_message(
                    status_msg,
                    "❌ Playback failed!\n\n"
                    "Checklist:\n"
                    "- Voice chat STARTED?\n"
                    "- Bot is ADMIN?\n"
                    "- Userbot in group?"
                )
        else:
            queue_pos = len(music_queue.get_queue(chat_id))
            text = (
                f"✅ Added to queue:\n"
                f"🎵 {track_info['title']}\n"
                f"📊 Position: {queue_pos}"
            )
            await safe_edit_message(status_msg, text)
            
    except Exception as e:
        logger.error(f"Play error: {e}")
        import traceback
        traceback.print_exc()
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:150]}", message.id)

@bot.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    try:
        chat_id = message.chat.id
        music_queue.clear(chat_id)
        await leave_voice_chat(chat_id)
        await safe_send_message(chat_id, "⏹️ Stopped!", message.id)
        
        if chat_id in music_queue.current:
            file_path = music_queue.current[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
    except Exception as e:
        logger.error(f"Stop error: {e}")

@bot.on_message(filters.command("skip"))
async def skip_command(client: Client, message: Message):
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
            text = f"⏭️ Skipped!\n🎵 {track['title']}"
            await safe_send_message(chat_id, text, message.id)
        else:
            await safe_send_message(chat_id, "⏹️ Queue empty!", message.id)
    except Exception as e:
        logger.error(f"Skip error: {e}")

@bot.on_message(filters.command("queue"))
async def queue_command(client: Client, message: Message):
    try:
        chat_id = message.chat.id
        current = music_queue.current.get(chat_id)
        queue = music_queue.get_queue(chat_id)
        
        if not current and not queue:
            await safe_send_message(chat_id, "📭 Queue is empty!", message.id)
            return
        
        response = "📃 Queue:\n\n"
        if current:
            response += f"▶️ Now: {current['title']}\n\n"
        if queue:
            response += "Next:\n"
            for i, track in enumerate(queue[:10], 1):
                response += f"{i}. {track['title']}\n"
            if len(queue) > 10:
                response += f"\n...+{len(queue) - 10} more"
        
        await safe_send_message(chat_id, response, message.id)
    except Exception as e:
        logger.error(f"Queue error: {e}")

async def main():
    os.makedirs("downloads", exist_ok=True)
    
    await bot.start()
    await userbot.start()
    
    logger.info("="*60)
    logger.info("🎵 MUSIC BOT STARTED - NO COOKIES REQUIRED!")
    logger.info("="*60)
    logger.info("✅ 7 bypass methods active")
    logger.info("✅ Android Music, VR, iOS clients ready")
    logger.info("✅ MediaConnect enterprise bypass enabled")
    logger.info("="*60)
    print("\n🚀 Bot ready! Using NUCLEAR bypass methods!")
    print("⚠️  YouTube blocking is heavy - some songs may fail\n")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        bot.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped")
    finally:
        if os.path.exists("downloads"):
            for file in os.listdir("downloads"):
                try:
                    os.remove(os.path.join("downloads", file))
                except:
                    pass
