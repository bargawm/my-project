# ================================================================
# 🤖 AI FILE SYSTEM ROBOT CLI
# Author  : Bargaw M
# Version : 3.1.0
# ================================================================

import os
import sys
import shutil
import argparse
import threading
import time
import getpass
import json
from pathlib import Path
from typing import List

# --- Dependency Handling ---
try:
    import requests
except ImportError:
    print("\n[CRITICAL] Missing 'requests' library.")
    print("Please run: pip install requests\n")
    sys.exit(1)

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        CYAN = GREEN = RED = MAGENTA = YELLOW = BLUE = WHITE = ""
    class Style:
        RESET_ALL = BRIGHT = DIM = ""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Optional dependency

# --- UI Components ---

class Spinner:
    """Shows a rotating spinner in the console during long operations."""
    def __init__(self, message: str = "Processing"):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._spin)

    def start(self):
        self.stop_event.clear()
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r") # Clear line
        sys.stdout.flush()

    def _spin(self):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not self.stop_event.is_set():
            frame = chars[i % len(chars)]
            sys.stdout.write(f"\r{Fore.CYAN}{frame} {self.message}...{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

def print_banner():
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
    ╔═══════════════════════════════════════════════╗
    ║          🤖 AI FILE SYSTEM ROBOT              ║
    ║       Intelligent Automation Assistant        ║
    ╚═══════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)

def print_success(msg: str):
    print(f"{Fore.GREEN}✔ {msg}{Style.RESET_ALL}")

def print_error(msg: str):
    print(f"{Fore.RED}✖ {msg}{Style.RESET_ALL}")

def print_info(msg: str):
    print(f"{Fore.BLUE}ℹ {msg}{Style.RESET_ALL}")

# --- Core Logic ---

class FileSystemEngine:
    @staticmethod
    def find_files(pattern: str, root_path: str = ".", recursive: bool = True) -> List[str]:
        print_info(f"Searching for '{pattern}' in {root_path}")
        root = Path(root_path)
        if not root.exists():
            print_error("Path does not exist.")
            return []
        
        glob_func = root.rglob if recursive else root.glob
        files = []
        try:
            files = [str(p.absolute()) for p in glob_func(pattern) if p.is_file()]
            print_success(f"Found {len(files)} file(s).")
        except Exception as e:
            print_error(f"Search failed: {e}")
            
        return files

    @staticmethod
    def move_files(file_paths: List[str], destination: str):
        dest = Path(destination)
        try:
            dest.mkdir(parents=True, exist_ok=True)
            print_info(f"Moving files to {dest}")
        except Exception as e:
            print_error(f"Could not create destination: {e}")
            return

        success_count = 0
        for f in file_paths:
            try:
                # Handle filename collisions by renaming if necessary could be added here
                # For now, simple move
                shutil.move(f, dest / Path(f).name)
                print(f"  {Fore.GREEN}→ Moved: {Path(f).name}{Style.RESET_ALL}")
                success_count += 1
            except Exception as e:
                print(f"  {Fore.RED}→ Failed: {Path(f).name} ({e}){Style.RESET_ALL}")
        
        if success_count > 0:
            print_success(f"Operation completed. Moved {success_count} files.")

class AIRobot:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.model = "mistralai/mixtral-8x7b-instruct"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _get_api_key(self) -> str:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            print(f"\n{Fore.YELLOW}[SETUP] API Key not found in environment.{Style.RESET_ALL}")
            print(f"You can get a key at: https://openrouter.ai/keys")
            try:
                while not key:
                    key = getpass.getpass(f"{Fore.MAGENTA}Enter OpenRouter API Key (hidden): {Style.RESET_ALL}").strip()
            except KeyboardInterrupt:
                print("\n")
                sys.exit(0)
        return key

    def get_code_from_ai(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "You are a Python code generator for file system operations. "
            "Your available tool is a class `FileSystemEngine` with methods:\n"
            "1. `find_files(pattern: str, root_path: str = '.', recursive: bool = True) -> List[str]`\n"
            "2. `move_files(file_paths: List[str], destination: str)`\n"
            "Return ONLY valid Python code. No markdown formatting (no ```python blocks). "
            "Do not import anything. Assume FileSystemEngine is available."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise ValueError(f"API Error: {data['error'].get('message', 'Unknown error')}")
                
            content = data["choices"][0]["message"]["content"]
            # cleanup potential markdown if the model hallucinates
            clean_code = content.replace("```python", "").replace("```", "").strip()
            return clean_code
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error connecting to AI: {e}")
        except Exception as e:
            raise RuntimeError(f"AI processing failed: {e}")

    def execute(self, prompt: str):
        spinner = Spinner("Thinking")
        try:
            spinner.start()
            code = self.get_code_from_ai(prompt)
        except Exception as e:
            spinner.stop()
            print_error(str(e))
            return
        finally:
            spinner.stop()

        print(f"\n{Fore.YELLOW}📋 EXECUTION PLAN:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
        print(f"{Style.BRIGHT}{code}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}\n")

        try:
            # Safer input loop
            confirm = input(f"{Fore.MAGENTA}Execute this plan? (y/N): {Style.RESET_ALL}").lower()
            if confirm == "y":
                print("")
                exec(code, {"FileSystemEngine": FileSystemEngine, "print": print})
            else:
                print_info("Operation cancelled.")
        except KeyboardInterrupt:
            print("\n")
            print_info("Operation cancelled.")
        except Exception as e:
            print_error(f"Execution error: {e}")

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="AI File System Robot")
    parser.add_argument("prompt", nargs="?", help="Natural language command")
    args = parser.parse_args()

    if not args.prompt:
        print(f"{Fore.YELLOW}Usage: python robot.py \"<your command>\"{Style.RESET_ALL}")
        print("Example: python robot.py \"Move all jpg files to the Images folder\"")
        return

    try:
        bot = AIRobot()
        bot.execute(args.prompt)
    except KeyboardInterrupt:
        print("\nGood bye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
