import signal
from pyppeteer import launch
import asyncio
from pathlib import Path
import os

async def safe_launch(*args, **kwargs):
    original_signal = signal.signal

    def silent_blocker(sig, handler):
        print(f"⚠️ [SafeLaunch] Ignored signal registration for sig={sig}")

    signal.signal = silent_blocker  # temporarily ignore
    try:
        return await launch(*args, **kwargs)
    finally:
        signal.signal = original_signal  # restore afterward

def run_async_safely(coroutine):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)

def clear_folder(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"⚠️ Folder '{folder}' does not exist.")
        return

    for item in folder.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                # Recursively delete all contents
                for root, dirs, files in os.walk(item, topdown=False):
                    for file in files:
                        Path(root, file).unlink()
                    for subdir in dirs:
                        Path(root, subdir).rmdir()
                item.rmdir()
        except Exception as e:
            print(f"❌ Failed to delete {item}: {e}")

    print(f"✅ Cleared contents of folder: {folder}")