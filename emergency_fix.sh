#!/bin/bash

echo "=================================="
echo "  EMERGENCY FIX FOR YOUTUBE BOT"
echo "=================================="
echo ""

# Update yt-dlp to absolute latest
echo "📦 Updating yt-dlp to latest version..."
pip3 install --upgrade --force-reinstall yt-dlp

echo ""
echo "✅ yt-dlp updated!"
echo ""

# Check version
echo "Current yt-dlp version:"
yt-dlp --version

echo ""
echo "=================================="
echo "  TESTING BYPASS METHODS"
echo "=================================="
echo ""

# Test 1: Android Music client
echo "Test 1: Android Music client..."
yt-dlp --extractor-args "youtube:player_client=android_music;player_skip=webpage,configs" \
  --print "%(title)s" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | head -n 5

echo ""

# Test 2: iOS Music client
echo "Test 2: iOS Music client..."
yt-dlp --extractor-args "youtube:player_client=ios_music" \
  --print "%(title)s" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | head -n 5

echo ""
echo "=================================="
echo "  INSTRUCTIONS"
echo "=================================="
echo ""
echo "If tests above show 'Sign in' errors:"
echo ""
echo "OPTION 1 - Wait and retry:"
echo "  YouTube blocking is temporary"
echo "  Wait 10-30 minutes and try again"
echo ""
echo "OPTION 2 - Use VPN:"
echo "  Your IP might be blocked"
echo "  Use a VPN to change IP address"
echo ""
echo "OPTION 3 - Try different videos:"
echo "  Some videos are more restricted"
echo "  Try popular music videos instead"
echo ""
echo "OPTION 4 - Use cookies (NOT RECOMMENDED):"
echo "  Export cookies from browser"
echo "  Use --cookies-from-browser chrome"
echo ""
echo "=================================="
echo ""
echo "Now restart your bot:"
echo "  python3 Telegram_music_bot.py"
echo ""