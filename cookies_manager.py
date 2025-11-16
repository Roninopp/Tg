#!/usr/bin/env python3
"""
Cookie Manager for Lavalink
Helps add, update, and test YouTube cookies
"""

import os
import sys
import subprocess
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message, status="info"):
    colors = {"success": Colors.GREEN, "error": Colors.RED, "warning": Colors.YELLOW, "info": Colors.BLUE}
    print(f"{colors.get(status, '')}{message}{Colors.END}")

def check_lavalink_folder():
    """Check if lavalink folder exists"""
    if not os.path.exists("lavalink"):
        print_status("✗ Lavalink folder not found!", "error")
        print_status("Run lavalink_setup.py first", "warning")
        return False
    return True

def backup_existing_cookies():
    """Backup existing cookies if they exist"""
    cookie_path = "lavalink/cookies.txt"
    if os.path.exists(cookie_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"lavalink/cookies_backup_{timestamp}.txt"
        
        try:
            with open(cookie_path, 'r') as f:
                content = f.read()
            with open(backup_path, 'w') as f:
                f.write(content)
            print_status(f"✓ Backed up existing cookies to {backup_path}", "success")
            return True
        except Exception as e:
            print_status(f"⚠ Could not backup cookies: {e}", "warning")
    return True

def add_cookies_interactive():
    """Add cookies interactively"""
    print_status("\n" + "="*60, "info")
    print_status("ADD YOUTUBE COOKIES", "info")
    print_status("="*60 + "\n", "info")
    
    print("How to get YouTube cookies:")
    print("1. Install browser extension: 'Get cookies.txt LOCALLY'")
    print("   Chrome: https://chrome.google.com/webstore (search 'get cookies.txt')")
    print("   Firefox: https://addons.mozilla.org (search 'cookies.txt')")
    print("")
    print("2. Go to youtube.com and login to your account")
    print("")
    print("3. Click the extension icon and click 'Export'")
    print("")
    print("4. Copy all the text")
    print("")
    
    print_status("Method 1: Paste cookies directly", "info")
    print("Method 2: Upload cookies.txt file")
    print("")
    
    choice = input("Choose method (1/2): ").strip()
    
    if choice == "1":
        print("\nPaste your cookies below (Ctrl+D when done on Linux, Ctrl+Z on Windows):")
        print("-" * 60)
        try:
            cookies_content = sys.stdin.read()
            
            if not cookies_content.strip():
                print_status("✗ No cookies provided", "error")
                return False
            
            # Backup existing
            backup_existing_cookies()
            
            # Save new cookies
            with open("lavalink/cookies.txt", "w") as f:
                f.write(cookies_content)
            
            print_status("\n✓ Cookies saved successfully!", "success")
            return True
            
        except Exception as e:
            print_status(f"✗ Error saving cookies: {e}", "error")
            return False
    
    elif choice == "2":
        file_path = input("\nEnter path to cookies.txt file: ").strip()
        
        if not os.path.exists(file_path):
            print_status("✗ File not found", "error")
            return False
        
        try:
            with open(file_path, 'r') as f:
                cookies_content = f.read()
            
            if not cookies_content.strip():
                print_status("✗ File is empty", "error")
                return False
            
            # Backup existing
            backup_existing_cookies()
            
            # Copy to lavalink folder
            with open("lavalink/cookies.txt", "w") as f:
                f.write(cookies_content)
            
            print_status("✓ Cookies saved successfully!", "success")
            return True
            
        except Exception as e:
            print_status(f"✗ Error reading file: {e}", "error")
            return False
    
    else:
        print_status("✗ Invalid choice", "error")
        return False

def update_lavalink_config():
    """Update application.yml to use cookies"""
    config_path = "lavalink/application.yml"
    
    if not os.path.exists(config_path):
        print_status("✗ application.yml not found", "error")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = f.read()
        
        # Check if cookies config already exists
        if "cookieFile:" in config:
            print_status("✓ Config already has cookie support", "success")
            return True
        
        # Add cookie config
        if "plugins:" in config:
            cookie_config = """  youtube:
    enabled: true
    cookieFile: ./cookies.txt
    clients:
      - MUSIC
      - ANDROID
      - WEB
"""
            config = config.replace("plugins:", f"plugins:\n{cookie_config}")
            
            with open(config_path, 'w') as f:
                f.write(config)
            
            print_status("✓ Updated application.yml to use cookies", "success")
            return True
        else:
            print_status("⚠ Could not find plugins section in config", "warning")
            print_status("You may need to manually add cookie config", "warning")
            return False
            
    except Exception as e:
        print_status(f"✗ Error updating config: {e}", "error")
        return False

def test_cookies():
    """Test if cookies are working"""
    print_status("\nTesting cookies...", "info")
    print_status("This requires Lavalink to be running", "warning")
    print("")
    
    try:
        import urllib.request
        import json
        
        # Try to connect to Lavalink
        req = urllib.request.Request(
            "http://localhost:2333/version",
            headers={"Authorization": "youshallnotpass"}
        )
        
        try:
            response = urllib.request.urlopen(req, timeout=5)
            version = response.read().decode()
            print_status(f"✓ Lavalink is running: {version}", "success")
        except Exception as e:
            print_status("✗ Lavalink is not running", "error")
            print_status("Start Lavalink first: cd lavalink && java -jar Lavalink.jar", "info")
            return False
        
        # Try a test search
        print_status("Testing YouTube search...", "info")
        
        search_url = "http://localhost:2333/v4/loadtracks?identifier=ytsearch:test"
        req = urllib.request.Request(
            search_url,
            headers={"Authorization": "youshallnotpass"}
        )
        
        try:
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode())
            
            if data.get("loadType") == "search" and data.get("data"):
                print_status("✓ YouTube search working!", "success")
                print_status(f"Found {len(data['data'])} results", "success")
                return True
            elif data.get("loadType") == "error":
                print_status("✗ YouTube search failed", "error")
                print_status(f"Error: {data.get('data', {}).get('message', 'Unknown')}", "error")
                print_status("\nPossible causes:", "warning")
                print_status("1. Cookies are expired or invalid", "info")
                print_status("2. YouTube is blocking requests", "info")
                print_status("3. Need to refresh cookies", "info")
                return False
            else:
                print_status("⚠ Unexpected response", "warning")
                return False
                
        except Exception as e:
            print_status(f"✗ Test failed: {e}", "error")
            return False
            
    except ImportError:
        print_status("✗ Required modules not found", "error")
        return False

def show_cookie_info():
    """Show information about current cookies"""
    cookie_path = "lavalink/cookies.txt"
    
    if not os.path.exists(cookie_path):
        print_status("✗ No cookies found", "error")
        return
    
    try:
        with open(cookie_path, 'r') as f:
            content = f.read()
        
        lines = content.strip().split('\n')
        cookie_count = sum(1 for line in lines if line.strip() and not line.startswith('#'))
        
        # Get file modification time
        mod_time = os.path.getmtime(cookie_path)
        mod_date = datetime.fromtimestamp(mod_time)
        days_old = (datetime.now() - mod_date).days
        
        print_status("\n" + "="*60, "info")
        print_status("COOKIE INFORMATION", "info")
        print_status("="*60 + "\n", "info")
        
        print(f"Cookie file: {cookie_path}")
        print(f"Cookies found: {cookie_count}")
        print(f"Last updated: {mod_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Age: {days_old} days old")
        
        if days_old > 20:
            print_status("\n⚠ Cookies are getting old (20+ days)", "warning")
            print_status("Consider refreshing them soon", "warning")
        elif days_old > 30:
            print_status("\n⚠ Cookies are very old (30+ days)", "error")
            print_status("They may not work anymore - refresh recommended", "error")
        else:
            print_status(f"\n✓ Cookies are fresh ({days_old} days old)", "success")
        
    except Exception as e:
        print_status(f"✗ Error reading cookies: {e}", "error")

def main_menu():
    """Show main menu"""
    while True:
        print_status("\n" + "="*60, "info")
        print_status("COOKIE MANAGER", "success")
        print_status("="*60 + "\n", "info")
        
        print("1. Add/Update cookies")
        print("2. View cookie information")
        print("3. Test cookies")
        print("4. Backup cookies")
        print("5. Exit")
        print("")
        
        choice = input("Choose option (1-5): ").strip()
        
        if choice == "1":
            if not check_lavalink_folder():
                continue
            
            if add_cookies_interactive():
                update_lavalink_config()
                print_status("\n✓ Cookies updated!", "success")
                print_status("Restart Lavalink for changes to take effect", "warning")
        
        elif choice == "2":
            if not check_lavalink_folder():
                continue
            show_cookie_info()
        
        elif choice == "3":
            if not check_lavalink_folder():
                continue
            test_cookies()
        
        elif choice == "4":
            if not check_lavalink_folder():
                continue
            backup_existing_cookies()
        
        elif choice == "5":
            print_status("\nGoodbye!", "success")
            break
        
        else:
            print_status("✗ Invalid choice", "error")

def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        print_status("\n\nExiting...", "info")
        sys.exit(0)
    except Exception as e:
        print_status(f"\n✗ Unexpected error: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
