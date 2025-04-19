import json
import re
import ollama
from termcolor import colored
import time
import random
import os

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
""".strip()

# Approved folder list
VALID_FOLDERS = {
    "anime", "games", "comics", "cyberpunk", "humor", "fantasy", "magic-the-gathering",
    "landscape", "workspace", "memes", "food", "music", "lego", "marvel", "dc",
    "history", "fashion", "philosophy", "science-fiction", "movies"
}

def extract_json(text):
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    return match.group(1) if match else text.strip()

def validate_dst_path(dst_path, original_filename):
    try:
        folder_name = dst_path.split("/")[0].strip().lower()
        if folder_name not in VALID_FOLDERS:
            print(colored(f"⚠️ Invalid folder '{folder_name}' — re-routing to 'uncategorized'", "yellow"))
            return os.path.join("uncategorized", os.path.basename(original_filename))
        return dst_path
    except Exception as e:
        print(colored(f"❌ Error validating dst_path: {e}", "red"))
        return os.path.join("uncategorized", os.path.basename(original_filename))

def create_file_tree(summaries: list, session=None):
    if not summaries:
        raise ValueError("Summaries list is empty — cannot create file tree.")

    client = session or ollama.Client()
    categorized_files = []
    log_entries = []

    for i, summary in enumerate(summaries):
        file_path = summary["file_path"]
        file_summary = summary["summary"]

        try:
            print(colored(f"[{i+1}/{len(summaries)}] Categorizing {file_path}", "cyan"))

            messages = [
                {"role": "system", "content": FILE_PROMPT},
                {"role": "user", "content": json.dumps({
                    "src_path": file_path,
                    "summary": file_summary
                })},
                {"role": "user", "content": "Respond ONLY with the JSON as described. No comments. Pure JSON."}
            ]

            response = client.chat(model="mistral:instruct", messages=messages)
            content = response["message"]["content"]
            print(colored(content, "yellow"))

            clean_json = extract_json(content)
            data = json.loads(clean_json)

            if "files" in data:
                for file in data["files"]:
                    validated_dst = validate_dst_path(file["dst_path"], file["src_path"])
                    log_entries.append(f"{file['src_path']} -> {validated_dst}")
                    file["dst_path"] = validated_dst
                    categorized_files.append(file)
            else:
                raise ValueError("Missing 'files' key")

            time.sleep(random.uniform(0.3, 0.8))  # throttle gently

        except Exception as e:
            print(colored(f"❌ Error categorizing file {file_path}: {e}", "red"))
            print(colored(f"🪵 Raw content: {response.get('message', {}).get('content', 'N/A')}", "magenta"))
            fallback_path = os.path.join("uncategorized", os.path.basename(file_path))
            log_entries.append(f"{file_path} -> {fallback_path}  # fallback")
            categorized_files.append({
                "src_path": file_path,
                "dst_path": fallback_path
            })

    # Write log to file
    with open("categorization_log.txt", "w", encoding="utf-8") as log_file:
        for entry in log_entries:
            log_file.write(entry + "\n")

    return categorized_files
