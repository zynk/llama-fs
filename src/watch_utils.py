import asyncio
import json
import os
import time
import ollama

# from groq import Groq
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.loader import get_dir_summaries, get_file_summary


class Handler(FileSystemEventHandler):
    def __init__(self, base_path, callback, queue):
        self.base_path = base_path
        self.callback = callback
        self.queue = queue
        self.events = []
        print(f"Watching directory {base_path}")

    async def set_summaries(self):
        print(f"Getting summaries for {self.base_path}")
        self.summaries = await get_dir_summaries(self.base_path)
        self.summaries_cache = {s["file_path"]: s for s in self.summaries}

    def update_summary(self, file_path):
        print(f"Updating summary for {file_path}")
        path = os.path.join(self.base_path, file_path)
        if not os.path.exists(path):
            self.summaries_cache.pop(file_path)
            return
        self.summaries_cache[file_path] = get_file_summary(path)
        self.summaries = list(self.summaries_cache.values())
        self.queue.put(
            {
                "files": [
                    {
                        "src_path": file_path,
                        "dst_path": file_path,
                        "summary": self.summaries_cache[file_path]["summary"],
                    }
                ]
            }
        )

    def on_created(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Created {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Deleted {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Modified {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        dest_path = os.path.relpath(event.dest_path, self.base_path)
        print(f"Moved {src_path} > {dest_path}")
        self.events.append({"src_path": src_path, "dst_path": dest_path})
        self.update_summary(src_path)
        self.update_summary(dest_path)
        print("Summaries: ", self.summaries)
        print("Events: ", self.events)
        files = self.callback(
            summaries=self.summaries, fs_events=json.dumps(
                {"files": self.events})
        )

        self.queue.put(files)


def create_file_tree(summaries, fs_events):
    FILE_PROMPT = """
You will be provided with a single file name and a summary of its contents.

Generate a new `dst_path` that includes:
- A folder name that categorizes the file based on its content that must be one of the following words: anime, games, comics, cyberpunk, humor, magic-the-gathering, movies, fantasy, landscape, workspace, memes, food, music, history, fashion, philosophy, science-fiction, marvel, dc, lego
- A new filename based on the subject of the file (make it more specific)

⚠️ Only generate one value for folder_name.
❌ Do not create subfolders or multiple folders.
❌ Do not reuse the same filename.
✔️ Output should contain a single folder name only, with no nested paths.
⚠️ Always include the folder name + filename + extension in dst_path.

Respond ONLY in the following JSON format:

```json
{
  "files": [
    {
      "src_path": "original_filename.ext",
      "dst_path": "folder_name/new_filename.ext"
    }
  ]
}
```
""".strip()

    WATCH_PROMPT = f"""
Here are a few examples of good file naming conventions to emulate, based on the files provided:

```json
{fs_events}
```

Include the above items in your response exactly as is, along all other proposed changes.
""".strip()

    client = ollama.Client()
    try:
        response = client.chat(
            model="mistral:instruct",
            messages=[
                {"role": "system", "content": FILE_PROMPT},
                {"role": "user", "content": json.dumps(summaries)},
            ]
        )
        return json.loads(response["message"]["content"])["files"]
    except Exception as e:
        print(f"❌ Failed to generate file tree with Ollama: {e}")
        return []
