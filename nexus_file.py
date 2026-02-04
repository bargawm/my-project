
import os
import json
import shutil
import requests
from pathlib import Path
from typing import List, Dict, Any

# =========================
# ANSI COLORS
# =========================
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


# =========================
# ENVIRONMENT CHECK
# =========================
def check_environment() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(f"{Colors.FAIL}ERROR: GEMINI_API_KEY environment variable not set.{Colors.ENDC}")
        print(f"{Colors.WARNING}Please set it using: set GEMINI_API_KEY=your_api_key{Colors.ENDC}")
        raise ValueError("Missing GEMINI_API_KEY environment variable")
    return api_key


# =========================
# CORE FILE FUNCTIONS
# =========================
def search_files(directory: str, extension: str, search_term: str) -> List[str]:
    base_path = Path(directory).expanduser()
    results = []

    for path in base_path.rglob(f"*{extension}"):
        if search_term.lower() in path.name.lower():
            results.append(str(path.resolve()))

    return results


def move_files(file_list: List[str], destination_folder: str) -> Dict[str, str]:
    dest = Path(destination_folder).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    moved = {}
    for file_path in file_list:
        src = Path(file_path)
        target = dest / src.name
        shutil.move(str(src), str(target))
        moved[str(src)] = str(target)

    return moved


# =========================
# HUMAN-IN-THE-LOOP PREVIEW
# =========================
def preview_changes(files: List[str], destination: str) -> bool:
    print(f"\n{Colors.HEADER}{Colors.BOLD}Proposed File Operations{Colors.ENDC}")
    print("-" * 80)
    for f in files:
        print(f"{f}  →  {destination}")
    print("-" * 80)

    choice = input(f"{Colors.WARNING}Proceed? [Y/N]: {Colors.ENDC}").strip().lower()
    return choice == "y"


# =========================
# GEMINI TOOL SCHEMA
# =========================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search files recursively by extension and keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "extension": {"type": "string"},
                    "search_term": {"type": "string"}
                },
                "required": ["directory", "extension", "search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_files",
            "description": "Move files safely to a destination folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "destination_folder": {"type": "string"}
                },
                "required": ["file_list", "destination_folder"]
            }
        }
    }
]


# =========================
# TOOL DISPATCHER
# =========================
def dispatch_tool(name: str, args: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
    """Dispatch tool calls. For move_files, returns args for preview instead of executing."""
    try:
        if name == "search_files":
            return search_files(**args)
        if name == "move_files":
            # Don't execute move_files here, return args for preview
            return {"action": "move_files_pending", "args": args}
        raise ValueError("Unknown tool")
    except (PermissionError, FileNotFoundError) as e:
        print(f"{Colors.FAIL}Filesystem error: {e}{Colors.ENDC}")
        return None


# =========================
# GOOGLE GEMINI API CALL
# =========================
def call_llm(api_key: str, user_prompt: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json"
    }

    # Convert tools to Gemini format
    gemini_tools = {
        "function_declarations": [
            tool["function"] for tool in TOOLS
        ]
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are a secure file management assistant. "
                            "Use tools only. Never assume destructive intent.\n\n"
                            f"User request: {user_prompt}"
                        )
                    }
                ]
            }
        ],
        "tools": [gemini_tools]
    }

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()
    return response.json()


# =========================
# MAIN
# =========================
def main() -> None:
    api_key = check_environment()
    print(f"{Colors.OKGREEN}NexusFile-CLI Ready{Colors.ENDC}")
    user_prompt = input(">> ")

    try:
        llm_response = call_llm(api_key, user_prompt)
        
        # Gemini response structure is different
        if "candidates" not in llm_response or not llm_response["candidates"]:
            print("No response from AI.")
            return
            
        candidate = llm_response["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        
        if not parts:
            print("No actionable response.")
            return
        
        # Check for function calls in parts
        function_calls = [part for part in parts if "functionCall" in part]
        
        if not function_calls:
            # Just text response
            text_parts = [part.get("text", "") for part in parts if "text" in part]
            print(" ".join(text_parts) or "No actionable response.")
            return

        context = {}

        for part in function_calls:
            func_call = part["functionCall"]
            tool_name = func_call["name"]
            args = func_call.get("args", {})
            result = dispatch_tool(tool_name, args, context)

            if tool_name == "search_files":
                if result:
                    context["files"] = result
                    print(f"{Colors.OKBLUE}Found {len(result)} file(s){Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}No files found.{Colors.ENDC}")

            if tool_name == "move_files":
                files = context.get("files", [])
                if not files:
                    print(f"{Colors.FAIL}No files to move.{Colors.ENDC}")
                    return

                if preview_changes(files, args["destination_folder"]):
                    moved = move_files(files, args["destination_folder"])
                    print(f"{Colors.OKGREEN}Successfully moved {len(moved)} file(s).{Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}Operation cancelled by user.{Colors.ENDC}")

    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}API timeout. Try again later.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
