import json
import re
import ollama

FILE_PROMPT = """
For each file, generate a new `dst_path` that includes:
- A relative folder path that categorizes the file based on its content
- A new filename based on its content, the filename should be a little more specific and detailed to the subject of the file

✅ Example:
If the file is "cool.jpg" and it's a funny reaction image, then:
  "dst_path": "memes/funny_meme.jpg"

⚠️ Never return just a folder name as the dst_path.
⚠️ Always include the full path + filename + extension in dst_path.

Your response format must be:

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
    """Extract JSON from a markdown-wrapped code block or plain text."""
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    return match.group(1) if match else text.strip()


def create_file_tree(summaries: list, session=None):
    if not summaries:
        raise ValueError("Summaries list is empty — cannot create file tree.")

    # Assume all summaries are image-based
    summaries_by_file = {
        summary["file_path"]: summary["summary"]
        for summary in summaries
    }

    client = ollama.Client()
    response = None

    try:
        response = client.chat(
            model="codellama:instruct",  # or just "codellama" if that's how it pulled
            messages=[
                {"role": "system", "content": FILE_PROMPT},
                {"role": "user", "content": json.dumps(summaries_by_file)},
                {"role": "user", "content": "Respond ONLY with the JSON as described. Do not explain anything. Absolutely no added summary statements or conclusions, PURE JSON ONLY!"}
            ],
        )

        raw_content = response["message"]["content"]
        print("📦 Model response content:\n", raw_content)

        clean_json = extract_json(raw_content)

        if not clean_json.strip():
            raise ValueError("Model returned empty content")

        data = json.loads(clean_json)

        if "files" not in data:
            raise ValueError("Missing 'files' key in parsed response")

        return data["files"]

    except Exception as e:
        print("❌ Error generating file tree with Ollama:", e)
        if response:
            print("🪵 Raw content:", response.get("message", {}).get("content", "Unknown"))
        else:
            print("🪵 Raw content: response was never set.")
        return []