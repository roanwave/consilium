"""
Consilium Launcher - Single-click startup with system tray control.

Double-click to start, right-click tray icon to exit.
"""

import subprocess
import sys
import time
import threading
import urllib.request
import os
import webbrowser
from pathlib import Path

# Check for required packages
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow", "-q"])
    import pystray
    from PIL import Image, ImageDraw


# Configuration
PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_PORT = 8001
FRONTEND_PORT = 3000
BACKEND_URL = f"http://localhost:{BACKEND_PORT}/health"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


class ConsiliumLauncher:
    def __init__(self):
        self.backend_proc = None
        self.frontend_proc = None
        self.icon = None
        self.browser = None
        self._shutdown_event = threading.Event()

    def create_icon_image(self):
        """Create a simple colored square icon."""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Draw a gold/amber square (war-accent color from the app)
        draw.rectangle([4, 4, size-4, size-4], fill='#D4AF37', outline='#8B7355', width=2)
        # Draw a simple "C" for Consilium
        draw.text((size//2 - 8, size//2 - 12), "C", fill='#1a1a1a')
        return image

    def start_backend(self):
        """Start the FastAPI backend server."""
        print("Starting backend...")

        # Windows: CREATE_NO_WINDOW flag hides the console
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        self.backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(BACKEND_PORT)],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        return self.backend_proc

    def start_frontend(self):
        """Start the Next.js frontend server."""
        print("Starting frontend...")

        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        # Use npm.cmd on Windows
        npm_cmd = "npm.cmd" if sys.platform == 'win32' else "npm"

        self.frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=PROJECT_ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            shell=False,
        )
        return self.frontend_proc

    def wait_for_server(self, url, name, timeout=60):
        """Wait for a server to become responsive."""
        print(f"Waiting for {name}...")
        start = time.time()
        while time.time() - start < timeout:
            if self._shutdown_event.is_set():
                return False
            try:
                urllib.request.urlopen(url, timeout=2)
                print(f"{name} is ready!")
                return True
            except Exception:
                time.sleep(1)
        print(f"Timeout waiting for {name}")
        return False

    def open_browser(self):
        """Open Chrome to the frontend URL."""
        print("Opening browser...")
        # Try to use Chrome specifically
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    subprocess.Popen([chrome_path, FRONTEND_URL])
                    return
                except Exception:
                    pass

        # Fallback to default browser
        webbrowser.open(FRONTEND_URL)

    def shutdown(self, icon=None, item=None):
        """Clean shutdown of all processes."""
        print("Shutting down Consilium...")
        self._shutdown_event.set()

        # Kill backend
        if self.backend_proc:
            try:
                self.backend_proc.terminate()
                self.backend_proc.wait(timeout=5)
            except Exception:
                self.backend_proc.kill()

        # Kill frontend (and its child processes on Windows)
        if self.frontend_proc:
            try:
                if sys.platform == 'win32':
                    # Kill the entire process tree
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.frontend_proc.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self.frontend_proc.terminate()
                    self.frontend_proc.wait(timeout=5)
            except Exception:
                pass

        # Stop the tray icon
        if self.icon:
            self.icon.stop()

        print("Consilium stopped.")

    def run_startup(self):
        """Background thread: start servers and open browser."""
        try:
            # Start servers
            self.start_backend()
            self.start_frontend()

            # Wait for backend first
            if not self.wait_for_server(BACKEND_URL, "Backend"):
                print("Backend failed to start")
                self.shutdown()
                return

            # Wait for frontend
            if not self.wait_for_server(FRONTEND_URL, "Frontend"):
                print("Frontend failed to start")
                self.shutdown()
                return

            # Open browser
            self.open_browser()

        except Exception as e:
            print(f"Startup error: {e}")
            self.shutdown()

    def run(self):
        """Main entry point."""
        print("=" * 50)
        print("Consilium Launcher")
        print("=" * 50)

        # Start servers in background thread
        startup_thread = threading.Thread(target=self.run_startup, daemon=True)
        startup_thread.start()

        # Create system tray icon
        menu = pystray.Menu(
            pystray.MenuItem("Consilium", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open in Browser", lambda: self.open_browser()),
            pystray.MenuItem("Exit Consilium", self.shutdown),
        )

        self.icon = pystray.Icon(
            "Consilium",
            self.create_icon_image(),
            "Consilium - Battle Engine",
            menu,
        )

        # Run the icon (blocks until icon.stop() is called)
        self.icon.run()


def main():
    launcher = ConsiliumLauncher()
    try:
        launcher.run()
    except KeyboardInterrupt:
        launcher.shutdown()


if __name__ == "__main__":
    main()
