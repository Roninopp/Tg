import os
import sys
import subprocess
import time
import logging
import aiohttp
import aiofiles
import yaml

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Use a recent, stable Lavalink version
LAVALINK_URL = "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.7/Lavalink.jar"
LAVALINK_FILE = "Lavalink.jar"
CONFIG_FILE = "application.yml"

class LavalinkManager:
    """
    Manages the automatic setup and lifecycle of the Lavalink server.
    """
    def __init__(self):
        self.lavalink_process = None

    async def start(self):
        """
        Main function to start the entire Lavalink setup process.
        """
        _logger.info("Starting Lavalink setup...")
        self._check_java()
        
        if not os.path.exists(LAVALINK_FILE):
            await self._download_lavalink()
        
        if not os.path.exists(CONFIG_FILE):
            self._generate_yml()
            
        if not os.path.exists("cookies.txt"):
            _logger.warning("cookies.txt not found! Creating an empty one.")
            _logger.warning("Please fill cookies.txt to access YouTube.")
            with open("cookies.txt", "w") as f:
                f.write("# Fill this file with your YouTube cookies in Netscape format.\n")
                f.write("# Use a browser extension like 'Get cookies.txt' to export them.\n")

        self._start_lavalink_process()
        await self._wait_for_lavalink()

    def _check_java(self):
        """
        Checks if Java (17 or higher) is installed and in PATH.
        """
        _logger.info("Checking for Java installation...")
        try:
            version_output = subprocess.check_output(
                ["java", "-version"], stderr=subprocess.STDOUT, text=True
            )
            
            # Basic check for version (Lavalink 4 needs Java 17+)
            if "version \"17" in version_output or "version \"21" in version_output:
                 _logger.info("Java 17+ found.")
            elif "version" in version_output:
                _logger.warning(f"Found Java, but it might be an older version: {version_output.splitlines()[0]}")
                _logger.warning("Lavalink 4 requires Java 17 or higher.")
            else:
                 _logger.info(f"Java found: {version_output.splitlines()[0]}")

        except (subprocess.CalledProcessError, FileNotFoundError):
            _logger.error("-------------------------------------------------")
            _logger.error("Java is NOT installed or not found in your PATH.")
            _logger.error("Please install Java 17 or higher to run Lavalink.")
            _logger.error("-------------------------------------------------")
            sys.exit(1)
        except Exception as e:
            _logger.error(f"An error occurred while checking Java version: {e}")
            sys.exit(1)

    async def _download_lavalink(self):
        """
        Downloads the Lavalink.jar file asynchronously.
        """
        _logger.info(f"Downloading {LAVALINK_FILE} from {LAVALINK_URL}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LAVALINK_URL) as response:
                    response.raise_for_status()  # Raise an error for bad status codes
                    
                    async with aiofiles.open(LAVALINK_FILE, 'wb') as f:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                sys.stdout.write(f"\rDownloading... {percent:.1f}% complete")
                                sys.stdout.flush()
            
            print("\nDownload complete.")
            _logger.info(f"Successfully downloaded {LAVALINK_FILE}.")

        except aiohttp.ClientError as e:
            _logger.error(f"Failed to download Lavalink.jar: {e}")
            if os.path.exists(LAVALINK_FILE):
                os.remove(LAVALINK_FILE) # Remove partial download
            sys.exit(1)

    def _generate_yml(self):
        """
        Generates the application.yml file with cookie support.
        """
        _logger.info(f"Generating {CONFIG_FILE}...")
        
        config = {
            'server': {
                'port': 2333,
                'address': '0.0.0.0'
            },
            'logging': {
                'level': {
                    'root': 'INFO',
                    'lavalink': 'INFO'
                }
            },
            'lavalink': {
                'server': {
                    'password': 'youshallnotpass',
                    'sources': {
                        'youtube': True,
                        'soundcloud': True,
                    },
                    'bufferDurationMs': 400,
                    'youtubeConfig': {
                        # We use cookieFile instead of email/password
                        'cookieFile': 'cookies.txt' 
                    },
                    'soundcloudConfig': {}
                }
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            _logger.info(f"Successfully generated {CONFIG_FILE}.")
        except Exception as e:
            _logger.error(f"Failed to write {CONFIG_FILE}: {e}")
            sys.exit(1)

    def _start_lavalink_process(self):
        """
        Starts the Lavalink.jar server as a background process.
        """
        _logger.info("Starting Lavalink server process...")
        command = ["java", "-jar", LAVALINK_FILE]
        
        try:
            # Start the process in the background.
            # Use Popen so it doesn't block.
            self.lavalink_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            _logger.info(f"Lavalink process started with PID: {self.lavalink_process.pid}")
            
        except Exception as e:
            _logger.error(f"Failed to start Lavalink process: {e}")
            sys.exit(1)

    async def _wait_for_lavalink(self):
        """
        Waits for the Lavalink server to be ready on port 2333.
        """
        _logger.info("Waiting for Lavalink to be ready...")
        retries = 30  # Wait for up to 30 seconds
        
        for i in range(retries):
            if self.lavalink_process.poll() is not None:
                # Process has terminated unexpectedly
                stderr_output = self.lavalink_process.stderr.read().decode('utf-8')
                _logger.error("Lavalink process terminated unexpectedly!")
                _logger.error("--- Lavalink Error Output ---")
                _logger.error(stderr_output)
                _logger.error("-----------------------------")
                _logger.error("Check your Java installation or application.yml.")
                sys.exit(1)

            try:
                async with aiohttp.ClientSession() as session:
                    # We don't need a valid password here, just to see if the port is open
                    async with session.get("http://localhost:2333/v4/info") as response:
                        if response.status == 200 or response.status == 401:
                            _logger.info("Lavalink server is up and running!")
                            return
            except aiohttp.ClientConnectorError:
                # Connection refused, server not ready yet
                pass
                
            await asyncio.sleep(1) # Wait 1 second before retrying

        _logger.error("Failed to connect to Lavalink server after 30 seconds.")
        self.stop()
        sys.exit(1)

    def stop(self):
        """
        Stops the Lavalink server process.
        """
        if self.lavalink_process:
            _logger.info("Stopping Lavalink server process...")
            self.lavalink_process.terminate()
            self.lavalink_process.wait(timeout=5) # Wait for it to close
            if self.lavalink_process.poll() is None:
                # Force kill if it doesn't terminate
                _logger.warning("Lavalink process did not terminate, force killing.")
                self.lavalink_process.kill()
            _logger.info("Lavalink server stopped.")
