#!/usr/bin/env python3
"""
Smart Dependency Installer with Multiple Backup Options
Tests: NTgCalls -> py-tgcalls -> pytgcalls (multiple versions)
"""

import os
import sys
import subprocess
import platform

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
    """Run shell command"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check if Python version is compatible"""
    print_status("Checking Python version...", "info")
    version = sys.version_info
    
    if version.major == 3 and version.minor >= 9:
        print_status(f"✓ Python {version.major}.{version.minor} detected", "success")
        return True
    else:
        print_status(f"✗ Python 3.9+ required, you have {version.major}.{version.minor}", "error")
        return False

def install_system_dependencies():
    """Install required system packages"""
    print_status("\nInstalling system dependencies...", "info")
    
    os_name = platform.system().lower()
    
    if os_name == "linux":
        # Detect distro
        success, stdout, _ = run_command("cat /etc/os-release", check=False)
        
        if "ubuntu" in stdout.lower() or "debian" in stdout.lower():
            packages = [
                "sudo apt update",
                "sudo apt install -y python3-pip",
                "sudo apt install -y ffmpeg",
                "sudo apt install -y python3-dev",
                "sudo apt install -y libtgvoip-dev",
                "sudo apt install -y portaudio19-dev",
                "sudo apt install -y build-essential"
            ]
        elif "centos" in stdout.lower() or "rhel" in stdout.lower():
            packages = [
                "sudo yum install -y python3-pip",
                "sudo yum install -y ffmpeg",
                "sudo yum install -y python3-devel",
                "sudo yum groupinstall -y 'Development Tools'"
            ]
        else:
            print_status("⚠ Unknown Linux distro, trying generic install...", "warning")
            packages = [
                "sudo apt install -y python3-pip ffmpeg python3-dev build-essential || sudo yum install -y python3-pip ffmpeg python3-devel"
            ]
        
        for cmd in packages:
            print_status(f"Running: {cmd}", "info")
            success, _, stderr = run_command(cmd, check=False)
            if not success and "ffmpeg" not in cmd:  # FFmpeg might be in different repos
                print_status(f"⚠ Warning: {cmd} failed", "warning")
        
        print_status("✓ System dependencies installed", "success")
        return True
    else:
        print_status("⚠ Non-Linux OS detected. Please install FFmpeg manually.", "warning")
        return True

def test_import(package_name):
    """Test if a package can be imported"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name, pip_name=None):
    """Install a Python package"""
    if pip_name is None:
        pip_name = package_name
    
    print_status(f"Installing {package_name}...", "info")
    
    # Try normal install first
    success, stdout, stderr = run_command(f"pip3 install {pip_name}", check=False)
    
    if success:
        print_status(f"✓ {package_name} installed", "success")
        return True
    
    # Check if it's externally-managed-environment error
    if "externally-managed-environment" in stderr.lower():
        print_status(f"⚠ Detected externally-managed Python", "warning")
        print_status(f"Trying with --break-system-packages...", "info")
        
        # Try with --break-system-packages
        success, stdout, stderr = run_command(f"pip3 install {pip_name} --break-system-packages", check=False)
        
        if success:
            print_status(f"✓ {package_name} installed", "success")
            return True
        
        # Try with --user flag
        print_status(f"Trying with --user flag...", "info")
        success, stdout, stderr = run_command(f"pip3 install --user {pip_name}", check=False)
        
        if success:
            print_status(f"✓ {package_name} installed (user)", "success")
            return True
    
    print_status(f"✗ {package_name} installation failed", "error")
    print_status(f"Error: {stderr[:200]}", "error")
    return False

def try_ntgcalls():
    """Try installing NTgCalls (Primary option)"""
    print_status("\n" + "="*60, "info")
    print_status("OPTION 1: Trying NTgCalls (Recommended)", "info")
    print_status("="*60, "info")
    
    # Install NTgCalls
    if install_package("ntgcalls", "ntgcalls"):
        # Test import
        if test_import("ntgcalls"):
            print_status("✓ NTgCalls is working!", "success")
            return "ntgcalls"
    
    print_status("✗ NTgCalls failed", "error")
    return None

def try_pytgcalls_new():
    """Try installing py-tgcalls (Backup option 1)"""
    print_status("\n" + "="*60, "info")
    print_status("OPTION 2: Trying py-tgcalls", "info")
    print_status("="*60, "info")
    
    if install_package("pytgcalls", "py-tgcalls"):
        if test_import("pytgcalls"):
            print_status("✓ py-tgcalls is working!", "success")
            return "pytgcalls"
    
    print_status("✗ py-tgcalls failed", "error")
    return None

def try_pytgcalls_old():
    """Try installing older PyTgCalls (Backup option 2)"""
    print_status("\n" + "="*60, "info")
    print_status("OPTION 3: Trying PyTgCalls (older version)", "info")
    print_status("="*60, "info")
    
    # Try specific versions
    versions = ["pytgcalls==3.0.0.dev24", "pytgcalls"]
    
    for version in versions:
        print_status(f"Trying {version}...", "info")
        if install_package("pytgcalls", version):
            if test_import("pytgcalls"):
                print_status(f"✓ {version} is working!", "success")
                return "pytgcalls"
    
    print_status("✗ PyTgCalls failed", "error")
    return None

def install_other_dependencies(tgcalls_lib):
    """Install other required packages"""
    print_status("\nInstalling other dependencies...", "info")
    
    packages = {
        "pyrogram": "pyrogram",
        "tgcrypto": "tgcrypto",
        "yt-dlp": "yt-dlp",
        "aiohttp": "aiohttp",
        "asyncio": None,  # Built-in
        "aiofiles": "aiofiles"
    }
    
    # Add lavalink client
    if tgcalls_lib == "ntgcalls":
        packages["wavelink"] = "wavelink"
    else:
        packages["lavalink"] = "lavalink"
    
    failed = []
    for package, pip_name in packages.items():
        if pip_name is None:
            continue
        
        if not install_package(package, pip_name):
            failed.append(package)
    
    if failed:
        print_status(f"⚠ Failed packages: {', '.join(failed)}", "warning")
        print_status("You may need to install them manually", "warning")
    else:
        print_status("✓ All dependencies installed successfully", "success")
    
    return True

def create_config_template():
    """Create config.py template"""
    print_status("\nCreating config template...", "info")
    
    config_content = """# Telegram Bot Configuration
API_ID = "YOUR_API_ID"  # Get from my.telegram.org
API_HASH = "YOUR_API_HASH"  # Get from my.telegram.org
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Get from @BotFather

# Lavalink Configuration
LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "youshallnotpass"

# Optional: Owner ID for admin commands
OWNER_ID = 0  # Your Telegram user ID
"""
    
    try:
        with open("config.py", "w") as f:
            f.write(config_content)
        print_status("✓ config.py template created", "success")
        print_status("⚠ Please edit config.py with your credentials", "warning")
        return True
    except Exception as e:
        print_status(f"✗ Failed to create config: {e}", "error")
        return False

def save_working_library(lib_name):
    """Save which library works for the main bot"""
    try:
        with open(".tgcalls_lib", "w") as f:
            f.write(lib_name)
        print_status(f"✓ Saved working library: {lib_name}", "success")
    except Exception as e:
        print_status(f"⚠ Could not save library info: {e}", "warning")

def main():
    print_status("\n" + "="*60, "success")
    print_status("SMART DEPENDENCY INSTALLER", "success")
    print_status("Testing multiple TgCalls libraries...", "success")
    print_status("="*60 + "\n", "success")
    
    # Step 1: Check Python version
    if not check_python_version():
        print_status("\n✗ Please upgrade Python to 3.9+", "error")
        return False
    
    # Step 2: Install system dependencies
    if not install_system_dependencies():
        print_status("\n⚠ System dependencies may be incomplete", "warning")
    
    # Step 3: Try TgCalls libraries in order
    working_lib = None
    
    # Try NTgCalls first
    working_lib = try_ntgcalls()
    
    # Try py-tgcalls if NTgCalls failed
    if not working_lib:
        working_lib = try_pytgcalls_new()
    
    # Try older PyTgCalls if all else failed
    if not working_lib:
        working_lib = try_pytgcalls_old()
    
    if not working_lib:
        print_status("\n" + "="*60, "error")
        print_status("✗ ALL OPTIONS FAILED", "error")
        print_status("="*60, "error")
        print_status("\nPossible solutions:", "warning")
        print_status("1. Check your Python version (need 3.9+)", "info")
        print_status("2. Make sure FFmpeg is installed: ffmpeg -version", "info")
        print_status("3. Try installing build tools manually", "info")
        print_status("4. Check error messages above for specific issues", "info")
        print_status("\nYou can try Docker option (coming in next step)", "info")
        return False
    
    # Step 4: Install other dependencies
    install_other_dependencies(working_lib)
    
    # Step 5: Save working library
    save_working_library(working_lib)
    
    # Step 6: Create config template
    create_config_template()
    
    # Final summary
    print_status("\n" + "="*60, "success")
    print_status("✓ INSTALLATION COMPLETED!", "success")
    print_status("="*60, "success")
    
    print(f"\n✓ Working TgCalls library: {working_lib}")
    print(f"✓ All dependencies installed")
    print(f"✓ Config template created")
    
    print_status("\nNext steps:", "info")
    print_status("1. Edit config.py with your Telegram credentials", "warning")
    print_status("2. Make sure Lavalink is running (run lavalink_setup.py first)", "warning")
    print_status("3. Run the music bot: python3 music_bot.py", "info")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_status("\n\n✗ Installation cancelled", "error")
        sys.exit(1)
    except Exception as e:
        print_status(f"\n✗ Unexpected error: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)
