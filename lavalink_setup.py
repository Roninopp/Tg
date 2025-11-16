#!/usr/bin/env python3
"""
Lavalink Setup Script - Automatic Installation
This script will:
1. Check system requirements
2. Install Java (required for Lavalink)
3. Download Lavalink.jar
4. Configure Lavalink with YouTube cookies
5. Start Lavalink server
"""

import os
import sys
import subprocess
import urllib.request
import json
import time

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message, status="info"):
    colors = {"success": Colors.GREEN, "error": Colors.RED, "warning": Colors.YELLOW, "info": Colors.BLUE}
    print(f"{colors.get(status, '')}{message}{Colors.END}")

def run_command(command, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_java():
    """Check if Java is installed"""
    print_status("Checking Java installation...", "info")
    success, stdout, _ = run_command("java -version", check=False)
    
    if success:
        print_status("✓ Java is already installed", "success")
        return True
    return False

def install_java():
    """Install Java (OpenJDK 17)"""
    print_status("Installing Java OpenJDK 17...", "info")
    
    # Detect OS
    success, stdout, _ = run_command("cat /etc/os-release", check=False)
    
    if "ubuntu" in stdout.lower() or "debian" in stdout.lower():
        commands = [
            "sudo apt update",
            "sudo apt install -y openjdk-17-jre-headless"
        ]
    elif "centos" in stdout.lower() or "rhel" in stdout.lower():
        commands = [
            "sudo yum install -y java-17-openjdk"
        ]
    else:
        print_status("⚠ Unknown OS. Please install Java 17 manually", "warning")
        return False
    
    for cmd in commands:
        print_status(f"Running: {cmd}", "info")
        success, _, stderr = run_command(cmd)
        if not success:
            print_status(f"✗ Failed: {stderr}", "error")
            return False
    
    print_status("✓ Java installed successfully", "success")
    return True

def download_lavalink():
    """Download latest Lavalink.jar"""
    print_status("Downloading Lavalink.jar...", "info")
    
    # Create lavalink directory
    os.makedirs("lavalink", exist_ok=True)
    os.chdir("lavalink")
    
    # Download Lavalink
    lavalink_url = "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar"
    
    try:
        print_status(f"Downloading from: {lavalink_url}", "info")
        urllib.request.urlretrieve(lavalink_url, "Lavalink.jar")
        print_status("✓ Lavalink.jar downloaded successfully", "success")
        return True
    except Exception as e:
        print_status(f"✗ Download failed: {e}", "error")
        return False

def create_application_yml():
    """Create Lavalink configuration file with YouTube cookies support"""
    print_status("Creating application.yml configuration...", "info")
    
    config = """server:
  port: 2333
  address: 0.0.0.0

lavalink:
  server:
    password: "youshallnotpass"
    sources:
      youtube: true
      bandcamp: true
      soundcloud: true
      twitch: true
      vimeo: true
      http: true
      local: false
    bufferDurationMs: 400
    frameBufferDurationMs: 5000
    youtubePlaylistLoadLimit: 6
    playerUpdateInterval: 5
    youtubeSearchEnabled: true
    soundcloudSearchEnabled: true
    gc-warnings: true

metrics:
  prometheus:
    enabled: false
    endpoint: /metrics

sentry:
  dsn: ""
  environment: ""

logging:
  file:
    path: ./logs/

  level:
    root: INFO
    lavalink: INFO

  logback:
    rollingpolicy:
      max-file-size: 1GB
      max-history: 30

plugins:
  youtube:
    enabled: true
    allowSearch: true
    allowDirectVideoIds: true
    allowDirectPlaylistIds: true
    clients:
      - MUSIC
      - ANDROID
      - WEB
"""
    
    try:
        with open("application.yml", "w") as f:
            f.write(config)
        print_status("✓ application.yml created", "success")
        return True
    except Exception as e:
        print_status(f"✗ Failed to create config: {e}", "error")
        return False

def setup_cookies():
    """Setup YouTube cookies"""
    print_status("\n" + "="*60, "info")
    print_status("YOUTUBE COOKIES SETUP", "info")
    print_status("="*60, "info")
    
    print("\nTo get YouTube cookies:")
    print("1. Install browser extension 'Get cookies.txt LOCALLY'")
    print("2. Go to youtube.com and login")
    print("3. Click extension and export cookies")
    print("4. Save as 'cookies.txt' in the lavalink folder")
    
    print_status("\nDo you want to add cookies now? (y/n): ", "warning")
    choice = input().strip().lower()
    
    if choice == 'y':
        print("\nPaste your cookies.txt content (Press Ctrl+D when done on Linux, Ctrl+Z on Windows):")
        try:
            cookies_content = sys.stdin.read()
            with open("cookies.txt", "w") as f:
                f.write(cookies_content)
            print_status("✓ Cookies saved to cookies.txt", "success")
            
            # Update application.yml to use cookies
            print_status("Updating application.yml to use cookies...", "info")
            with open("application.yml", "r") as f:
                config = f.read()
            
            # Add cookie config
            cookie_config = """
    cookieFile: ./cookies.txt
"""
            config = config.replace("plugins:", f"plugins:{cookie_config}")
            
            with open("application.yml", "w") as f:
                f.write(config)
            
            print_status("✓ Cookies configured in Lavalink", "success")
            return True
        except Exception as e:
            print_status(f"⚠ Cookie setup skipped: {e}", "warning")
            print_status("You can add cookies later by creating cookies.txt file", "info")
    else:
        print_status("⚠ Skipping cookies. You can add them later.", "warning")
        print_status("To add cookies later: Create 'cookies.txt' in lavalink folder", "info")
    
    return True

def create_start_script():
    """Create convenient start script"""
    print_status("Creating start script...", "info")
    
    start_script = """#!/bin/bash
echo "Starting Lavalink Server..."
java -jar Lavalink.jar
"""
    
    try:
        with open("start_lavalink.sh", "w") as f:
            f.write(start_script)
        os.chmod("start_lavalink.sh", 0o755)
        print_status("✓ start_lavalink.sh created", "success")
        return True
    except Exception as e:
        print_status(f"✗ Failed to create start script: {e}", "error")
        return False

def create_systemd_service():
    """Create systemd service for auto-start"""
    print_status("\nDo you want to create systemd service (auto-start on boot)? (y/n): ", "warning")
    choice = input().strip().lower()
    
    if choice != 'y':
        return True
    
    current_dir = os.getcwd()
    service_content = f"""[Unit]
Description=Lavalink Music Server
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={current_dir}
ExecStart=/usr/bin/java -jar {current_dir}/Lavalink.jar
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open("/tmp/lavalink.service", "w") as f:
            f.write(service_content)
        
        run_command("sudo mv /tmp/lavalink.service /etc/systemd/system/")
        run_command("sudo systemctl daemon-reload")
        run_command("sudo systemctl enable lavalink")
        
        print_status("✓ Systemd service created", "success")
        print_status("  Start: sudo systemctl start lavalink", "info")
        print_status("  Stop: sudo systemctl stop lavalink", "info")
        print_status("  Status: sudo systemctl status lavalink", "info")
        return True
    except Exception as e:
        print_status(f"⚠ Systemd service creation failed: {e}", "warning")
        return False

def test_lavalink():
    """Test if Lavalink is accessible"""
    print_status("\nStarting Lavalink server for testing...", "info")
    print_status("This will take 10-15 seconds...", "warning")
    
    # Start Lavalink in background
    process = subprocess.Popen(
        ["java", "-jar", "Lavalink.jar"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    time.sleep(15)
    
    # Test connection
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 2333))
        sock.close()
        
        if result == 0:
            print_status("✓ Lavalink is running on port 2333!", "success")
            process.terminate()
            return True
        else:
            print_status("✗ Lavalink is not accessible on port 2333", "error")
            process.terminate()
            return False
    except Exception as e:
        print_status(f"✗ Connection test failed: {e}", "error")
        process.terminate()
        return False

def main():
    print_status("\n" + "="*60, "info")
    print_status("LAVALINK AUTOMATIC SETUP SCRIPT", "success")
    print_status("="*60 + "\n", "info")
    
    # Step 1: Check/Install Java
    if not check_java():
        if not install_java():
            print_status("\n✗ Setup failed: Could not install Java", "error")
            return False
    
    # Step 2: Download Lavalink
    if not download_lavalink():
        print_status("\n✗ Setup failed: Could not download Lavalink", "error")
        return False
    
    # Step 3: Create configuration
    if not create_application_yml():
        print_status("\n✗ Setup failed: Could not create configuration", "error")
        return False
    
    # Step 4: Setup cookies
    setup_cookies()
    
    # Step 5: Create start script
    create_start_script()
    
    # Step 6: Create systemd service (optional)
    create_systemd_service()
    
    # Final summary
    print_status("\n" + "="*60, "success")
    print_status("✓ LAVALINK SETUP COMPLETED SUCCESSFULLY!", "success")
    print_status("="*60, "success")
    
    print("\nLavalink Details:")
    print(f"  📁 Location: {os.getcwd()}")
    print(f"  🌐 Host: localhost")
    print(f"  🔌 Port: 2333")
    print(f"  🔑 Password: youshallnotpass")
    
    print("\nTo start Lavalink:")
    print(f"  cd {os.getcwd()}")
    print(f"  ./start_lavalink.sh")
    print("\nOr:")
    print(f"  java -jar Lavalink.jar")
    
    print_status("\n⚠ IMPORTANT: Keep Lavalink running when using the music bot!", "warning")
    
    # Ask if user wants to test
    print_status("\nDo you want to test Lavalink now? (y/n): ", "warning")
    choice = input().strip().lower()
    
    if choice == 'y':
        test_lavalink()
    
    print_status("\n✓ You can now run the music bot setup script!", "success")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("\n\n✗ Setup cancelled by user", "error")
        sys.exit(1)
    except Exception as e:
        print_status(f"\n✗ Unexpected error: {e}", "error")
        sys.exit(1)
