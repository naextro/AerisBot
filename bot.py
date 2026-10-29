"""
Pterodactyl / Direct Entrypoint
===============================
Allows running directly via 'python bot.py' or through Pterodactyl panels
where APP_PY_FILE is set to 'bot.py'. Automatically configures PYTHONPATH.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path so 'src' imports always resolve
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Also ensure local pip packages installed by Pterodactyl (.local) are discoverable
LOCAL_SITE = BASE_DIR / ".local" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if LOCAL_SITE.exists() and str(LOCAL_SITE) not in sys.path:
    sys.path.insert(0, str(LOCAL_SITE))

from src.main import start

if __name__ == "__main__":
    start()
