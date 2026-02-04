# ================================================================
# 🤖 AI FILE SYSTEM ROBOT CLI
# Author  : Bargaw M
# Version : 3.0.0
# Year    : 2026
# ================================================================

import os
import sys
import shutil
import argparse
from pathlib import Path
from typing import List
import requests
from dotenv import load_dotenv
from colorama import init, Fore, Style

init(autoreset=True)
load_dotenv()


class FileSystemEngine:
    @staticmethod
    def find_files(pattern: str, root_path: str = ".", recursive: bool = True) -> List[str]:
        print(f"{Fore.CYAN}[SCAN]{Style.RESET_ALL} Searching for '{pattern}' in {root_path}")
        root = Path(root_path)
        if not root.exists():
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Path does not exist.")
            return []
        glob_func = root.rglob if recursive else root.glob
        files = [str(p.absolute()) for p in glob_func(pattern) if p.is_file()]
        print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {len(files)} file(s) found.")
        return files

    @staticmethod
    def move_files(file_paths: List[str], destination: str):
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        print(f"{Fore.CYAN}[MOVE]{Style.RESET_ALL} Moving files to {dest}")
        for f in file_paths:
            try:
                shutil.move(f, dest / Path(f).name)
                print(f"{Fore.GREEN}✔ {Path(f).name}")
            except Exception as e:
                print(f"{Fore.RED}✖ Failed: {f} → {e}")


class AIRobot:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "mistralai/mixtral-8x7b-instruct"
        if not self.api_key:
            print(f"{Fore.RED}[CONFIG ERROR]{Style.RESET_ALL} API key missing in .env")
            sys.exit(1)

    def get_code_from_ai(self, prompt: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return only Python code using FileSystemEngine."},
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post(url, headers=headers, json=payload).json()
        content = response["choices"][0]["message"]["content"]
        return content.replace("```python", "").replace("```", "").strip()

    def execute(self, prompt: str):
        print(f"{Fore.MAGENTA}[AI PROCESSING]{Style.RESET_ALL} {prompt}")
        code = self.get_code_from_ai(prompt)
        print(f"\n--- EXECUTION PLAN ---\n{code}\n-----------------------\n")
        if input("Execute? (y/N): ").lower() == "y":
            exec(code, {"FileSystemEngine": FileSystemEngine})


def main():
    print(f"{Fore.CYAN}AI FILE SYSTEM ROBOT v3.0 | Bargaw M{Style.RESET_ALL}")
    parser = argparse.ArgumentParser(description="AI Automation CLI")
    parser.add_argument("prompt", help="Natural language command")
    args = parser.parse_args()
    bot = AIRobot()
    bot.execute(args.prompt)


if __name__ == "__main__":
    main()
