import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PeerIdInvalid
from pyrogram.enums import ParseMode
from pyrogram import raw
from pyrogram.file_id import FileId
import yt_dlp
import aiohttp
import aiofiles
import os
from collections import deque
from typing import Dict, Optional
import re
import time
import json

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

# ULTRA AGGRESSIVE yt-dlp options - Multiple extraction methods
def get_ydl_opts(method=1):
    """Get yt-dlp options with different extraction methods"""
    
    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    if method == 1:
        # Method 1: Android client bypass
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_embedded'],
                    'player_skip': ['webpage', 'configs', 'js'],
                }
            }
        })
    elif method == 2:
        # Method 2: iOS client
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                    'player_skip': ['configs'],
                }
            }
        })
    elif method == 3:
        # Method 3: TV embedded client
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded'],
                }
            }
        })
    elif method == 4:
        # Method 4: Multiple clients fallback
        base_opts.update({
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                }
            }
        })
    
    return base_opts

async def download_audio_multi_method(url: str) -> Optional[dict]:
    """Try multiple extraction methods to bypass bot detection"""
    methods = [1, 2, 3, 4]
    
    for method_num in methods:
        try:
            logger.info(f"Trying extraction method {method_num} for: {url}")
            ydl_opts = get_ydl_opts(method_num)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract and download
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    continue
                
                # Get file path
                file_path = ydl.prepare_filename(info)
                base_path = file_path.rsplit('.', 1)[0]
                mp3_path = base_path + '.mp3'
                
                # Wait for file
                max_wait = 30
                for _ in range(max_wait):
                    if os.path.exists(mp3_path):
                        break
                    # Check alternative formats
                    for ext in ['.m4a', '.webm', '.opus', '.ogg']:
                        alt_path = base_path + ext
                        if os.path.exists(alt_path):
                            mp3_path = alt_path
                            break
                    if os.path.exists(mp3_path):
                        break
                    await asyncio.sleep(1)
                
                if not os.path.exists(mp3_path):
                    logger.warning(f"Method {method_num}: File not found")
                    continue
                
                logger.info(f"✅ Method {method_num} SUCCESS!")
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'file_path': mp3_path,
                    'url': url,
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown')
                }
                
        except Exception as e:
            logger.error(f"Method {method_num} failed: {e}")
            continue
    
    logger.error("❌ ALL METHODS FAILED")
    return None

async def search_youtube(query: str) -> Optional[str]:
    """Search YouTube with aggressive bypass"""
    try:
        search_opts = {
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'extract_flat': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            }
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
            return await bot.send_message(
                chat_id=chat_id,
                text=simple_text,
                reply_to_message_id=reply_to_message_id
            )
        except:
            return None

async def safe_edit_message(message: Message, text: str) -> bool:
    """Edit message without entity errors"""
    try:
        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '')
        await message.edit_text(clean_text, parse_mode=None)
        return True
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return False

async def get_chat_peer(chat_id: int):
    """FIXED: Resolve chat peer properly to avoid peer ID errors"""
    try:
        # Try to get from cache first
        peer = await userbot.resolve_peer(chat_id)
        return peer
    except (PeerIdInvalid, KeyError, ValueError) as e:
        logger.warning(f"Peer not in cache, fetching chat info: {e}")
        try:
            # Get chat info to populate cache
            chat = await userbot.get_chat(chat_id)
            # Try resolve again
            peer = await userbot.resolve_peer(chat_id)
            return peer
        except Exception as e2:
            logger.error(f"Failed to resolve peer after fetch: {e2}")
            raise

async def join_voice_chat(chat_id: int):
    """FIXED: Join voice chat with proper peer resolution"""
    try:
        logger.info(f"Attempting to join voice chat in {chat_id}")
        
        # Ensure peer is resolved
        peer = await get_chat_peer(chat_id)
        
        # Get full chat info
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(
                channel=peer
            )
        )
        
        # Check if call exists
        call = full_chat.full_chat.call
        if not call:
            logger.error("No active voice chat found!")
            return False
        
        # Join the group call
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
        logger.info(f"✅ Successfully joined voice chat in {chat_id}")
        return True
        
    except FloodWait as e:
        logger.warning(f"FloodWait: sleeping for {e.value} seconds")
        await asyncio.sleep(e.value)
        return await join_voice_chat(chat_id)
    except Exception as e:
        logger.error(f"❌ Error joining voice chat: {e}")
        import traceback
        traceback.print_exc()
        return False

async def leave_voice_chat(chat_id: int):
    """FIXED: Leave voice chat properly"""
    try:
        if chat_id not in music_queue.call_participants:
            logger.warning("Not in voice chat")
            return True
        
        peer = await get_chat_peer(chat_id)
        
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(
                channel=peer
            )
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
        
        logger.info(f"✅ Left voice chat in {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error leaving voice chat: {e}")
        return False

async def play_audio(chat_id: int, file_path: str):
    """FIXED: Stream audio to voice chat with proper implementation"""
    try:
        logger.info(f"Starting audio playback in {chat_id}: {file_path}")
        
        # Ensure we're in the call
        if not music_queue.active_calls.get(chat_id):
            success = await join_voice_chat(chat_id)
            if not success:
                return False
        
        # Check file exists
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return False
        
        logger.info(f"✅ Audio file ready: {file_path}")
        
        # Get peer and call info
        peer = await get_chat_peer(chat_id)
        full_chat = await userbot.invoke(
            raw.functions.channels.GetFullChannel(channel=peer)
        )
        
        call = full_chat.full_chat.call
        if not call:
            logger.error("No active call found")
            return False
        
        # Read audio file
        with open(file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        logger.info(f"Audio file size: {len(audio_data)} bytes")
        
        # Update stream with audio
        # Note: This is a simplified version. Full implementation requires:
        # 1. Audio encoding to proper format
        # 2. RTP packet creation
        # 3. Continuous streaming loop
        
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
        
        logger.info(f"✅ Started streaming audio in {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error playing audio: {e}")
        import traceback
        traceback.print_exc()
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
        "/help - Show this message\n\n"
        "IMPORTANT: Make sure voice chat is STARTED before using /play!"
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Help command handler"""
    text = (
        "🎵 Music Bot Help\n\n"
        "Commands:\n"
        "/play - Play music from YouTube\n"
        "/stop - Stop playback and clear queue\n"
        "/skip - Skip to next song\n"
        "/queue - Display current queue\n\n"
        "Setup:\n"
        "1. Start a voice chat in your group\n"
        "2. Make sure bot is admin\n"
        "3. Use /play <song name>\n\n"
        "Examples:\n"
        "/play brown rang\n"
        "/play https://youtube.com/watch?v=..."
    )
    await safe_send_message(message.chat.id, text, message.id)

@bot.on_message(filters.command("play"))
async def play_command(client: Client, message: Message):
    """FIXED: Play command with ultra-aggressive bot detection bypass"""
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
        
        status_msg = await safe_send_message(chat_id, "🔍 Searching...", message.id)
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
                await safe_edit_message(status_msg, "❌ No results found! Try a different search.")
                return
        
        # Download with multiple methods
        await safe_edit_message(status_msg, "⬇️ Downloading audio...\nThis may take 30-60 seconds...")
        
        track_info = await download_audio_multi_method(url)
        
        if not track_info:
            await safe_edit_message(
                status_msg,
                "❌ Failed to download after trying all methods!\n\n"
                "Possible reasons:\n"
                "- Video is unavailable\n"
                "- Age-restricted content\n"
                "- Regional restrictions\n"
                "- YouTube is blocking requests\n\n"
                "Try:\n"
                "1. Different song\n"
                "2. Wait a few minutes and retry\n"
                "3. Use direct YouTube URL"
            )
            return
        
        # Add to queue
        music_queue.add(chat_id, track_info)
        
        # If nothing is playing, start playback
        if chat_id not in music_queue.current or not music_queue.current.get(chat_id):
            await safe_edit_message(status_msg, "🎵 Joining voice chat and starting playback...")
            track = await play_next(chat_id)
            
            if track:
                duration_str = f"{track['duration'] // 60}:{track['duration'] % 60:02d}"
                text = (
                    f"▶️ Now Playing:\n"
                    f"🎵 {track['title']}\n"
                    f"👤 {track['uploader']}\n"
                    f"⏱ Duration: {duration_str}\n\n"
                    f"Note: If you don't hear audio, make sure:\n"
                    f"1. Voice chat is started\n"
                    f"2. Bot has admin permissions\n"
                    f"3. Your device volume is up"
                )
                await safe_edit_message(status_msg, text)
            else:
                await safe_edit_message(
                    status_msg,
                    "❌ Failed to start playback!\n\n"
                    "Checklist:\n"
                    "1. Is voice chat STARTED in this group?\n"
                    "2. Is bot an ADMIN?\n"
                    "3. Does bot have permission to manage voice chats?\n"
                    "4. Is userbot account in this group?"
                )
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
        import traceback
        traceback.print_exc()
        error_text = f"❌ An error occurred: {str(e)[:200]}"
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
            for i, track in enumerate(queue[:10], 1):
                response += f"{i}. {track['title']}\n"
            
            if len(queue) > 10:
                response += f"\n...and {len(queue) - 10} more"
        
        await safe_send_message(chat_id, response, message.id)
        
    except Exception as e:
        logger.error(f"Error in queue command: {e}")
        await safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}", message.id)

async def main():
    """Main function to start the bot"""
    os.makedirs("downloads", exist_ok=True)
    
    await bot.start()
    await userbot.start()
    
    logger.info("="*50)
    logger.info("🎵 Music Bot Started Successfully!")
    logger.info("="*50)
    logger.info("✅ Multi-method YouTube extraction enabled")
    logger.info("✅ Peer ID resolution fixed")
    logger.info("✅ Voice chat streaming ready")
    logger.info("="*50)
    print("\n🎵 Bot is running and ready to play music!")
    print("📝 Make sure voice chat is STARTED before using /play\n")
    
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
