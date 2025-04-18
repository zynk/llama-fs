import json
import re
import ollama
from termcolor import colored
import time
import random

FILE_PROMPT = """
You will be provided with a single file and a summary of its contents.

Generate a new `dst_path` that includes:
- A **relative folder path** that categorizes the file based on its content
- A **new filename** based on the subject of the file (make it more specific and descriptive)

Only use one of the following folders to categorize the file, here is the Categories List:
anime
gaming
comics
cyberpunk
funny
infographics
magic the gathering
pixel
landscape
workspace
movies
memes
art
food
music
history
fashion
philosophy
science fiction
space
uncategorized

⚠️ Never create a dst_path using a folder name that is not on the Categories list!
⚠️ Never return just a folder name as the dst_path.
⚠️ Always include the full path + filename + extension in dst_path.
⚠️ Do not repeat the original filename, make it more descriptive based on content.
⚠️ If the content doesn't fit any category, use the "uncategorized" folder.

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

def extract_json(text):
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    return match.group(1) if match else text.strip()

def create_file_tree(summaries: list, session=None):
    if not summaries:
        raise ValueError("Summaries list is empty — cannot create file tree.")

    client = session or ollama.Client()
    categorized_files = []

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

            response = client.chat(model="codellama:instruct", messages=messages)
            content = response["message"]["content"]
            print(colored(content, "yellow"))

            clean_json = extract_json(content)
            data = json.loads(clean_json)

            if "files" in data:
                categorized_files.extend(data["files"])
            else:
                raise ValueError("Missing 'files' key")

            time.sleep(random.uniform(0.4, 0.9))  # throttle gently

        except Exception as e:
            print(colored(f"❌ Error categorizing file {file_path}: {e}", "red"))
            print(colored(f"🪵 Raw content: {response.get('message', {}).get('content', 'N/A')}", "magenta"))

    return categorized_files
