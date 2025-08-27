import os
DEFAULT_CACHE_DIR = os.path.expanduser("~/.macos-fonts-mcp")
DEFAULT_OUT_DIR   = os.path.join(DEFAULT_CACHE_DIR, "out")
def ensure_dirs():
    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)
    os.makedirs(DEFAULT_OUT_DIR, exist_ok=True)
