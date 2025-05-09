import asyncio
import json
import os
from collections import defaultdict
import random

import colorama
import ollama
import weave
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.schema import ImageDocument
from llama_index.core.node_parser import TokenTextSplitter
from termcolor import colored

colorama.init()


async def get_dir_summaries(path: str):
    doc_dicts = load_documents(path)
    summaries = await get_summaries(doc_dicts)
    for summary in summaries:
        summary["file_path"] = os.path.relpath(summary["file_path"], path)
    return summaries


def load_documents(path: str):
    reader = SimpleDirectoryReader(
        input_dir=path,
        recursive=True,
        required_exts = [
            # Documents
            ".pdf", ".txt", ".doc", ".docx", ".rtf", ".md",

            # Images
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"
        ]
    )
    splitter = TokenTextSplitter(chunk_size=6144)
    documents = []
    for docs in reader.iter_data():
        if len(docs) > 1:
            for d in docs:
                contents = splitter.split_text("\n".join(d.text))
                text = contents[0] if contents else ""
                documents.append(Document(text=text, metadata=docs[0].metadata))
        else:
            documents.append(docs[0])
    return documents


async def summarize_document(doc):
    PROMPT = """
You will be provided with the contents of a file along with its metadata.

Your job is to provide a detailed and content-specific summary. The purpose is to help organize and rename the file based on **its actual subject**, not just its format or type.

Your summary should:
- Identify the core subject of the file.

Respond in JSON format with this schema:

```json
{
    "file_path": "path to the file including name",
    "summary": "summary of the content"
}
```
""".strip()

    client = ollama.AsyncClient()
    response = await client.chat(
        model="mistral:instruct",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(doc)},
        ],
    )
    try:
        summary = json.loads(response["message"]["content"])
    except Exception:
        summary = {
            "file_path": doc.get("file_path", "unknown"),
            "summary": response["message"]["content"]
        }

    print(colored(summary["file_path"], "green"))
    print(summary["summary"])
    print("-" * 80 + "\n")
    return summary

async def summarize_image_document(doc: ImageDocument):
    PROMPT = """
What is this a picture of?
""".strip()

    client = ollama.AsyncClient()
    response = await client.chat(
        model="llava:13b",
        messages=[
            {"role": "user", "content": PROMPT, "images": [doc.image_path]}
        ],
        options={"num_predict": 128}
    )

    summary = {
        "file_path": doc.image_path,
        "summary": response["message"]["content"],
    }

    print(colored(summary["file_path"], "green"))
    print(summary["summary"])
    print("-" * 80 + "\n")
    return summary




async def dispatch_summarize_document(doc, _client=None):
    if isinstance(doc, ImageDocument):
        return await summarize_image_document(doc)
    elif isinstance(doc, Document):
        return await summarize_document({"content": doc.text, **doc.metadata})
    else:
        raise ValueError("Document type not supported")

async def get_summaries(documents):
    summaries = []
    for i, doc in enumerate(documents):
        try:
            print(colored(f"[{i+1}/{len(documents)}] Summarizing...", "cyan"))
            summary = await dispatch_summarize_document(doc)
            summaries.append(summary)
            await asyncio.sleep(random.uniform(0.1, 0.1)) # gentle delay to avoid overload
        except Exception as e:
            print(colored(f"Failed to summarize document: {e}", "red"))
    return summaries

def merge_summary_documents(summaries, metadata_list):
    list_summaries = defaultdict(list)
    for item in summaries:
        list_summaries[item["file_path"]].append(item["summary"])

    file_summaries = {
        path: ". ".join(summaries) for path, summaries in list_summaries.items()
    }

    file_list = [
        {"summary": file_summaries[file["file_path"]], **file} for file in metadata_list
    ]
    return file_list


# ===========================
# SYNC VERSIONS
# ===========================

def get_file_summary(path: str):
    reader = SimpleDirectoryReader(input_files=[path]).iter_data()
    docs = next(reader)
    splitter = TokenTextSplitter(chunk_size=6144)
    text = splitter.split_text("\n".join([d.text for d in docs]))[0]
    doc = Document(text=text, metadata=docs[0].metadata)
    summary = dispatch_summarize_document_sync(doc)
    return summary


def dispatch_summarize_document_sync(doc):
    if isinstance(doc, ImageDocument):
        return summarize_image_document_sync(doc)
    elif isinstance(doc, Document):
        return summarize_document_sync({"content": doc.text, **doc.metadata})
    else:
        raise ValueError("Document type not supported")


def summarize_document_sync(doc):
    PROMPT = """
You will be provided with the contents of a file along with its metadata.

Your job is to provide a detailed and content-specific summary. The purpose is to help organize and rename the file based on **its actual subject**, not just its format or type.

Your summary should:
- Identify the core subject of the file.

Respond in JSON format with this schema:

```json
{
    "file_path": "path to the file including name",
    "summary": "summary of the content"
}
```
""".strip()

    client = ollama.Client()
    response = client.chat(
        model="mistral:instruct",
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(doc)},
        ],
    )

    try:
        summary = json.loads(response["message"]["content"])
    except Exception:
        summary = {
            "file_path": doc.get("file_path", "unknown"),
            "summary": response["message"]["content"]
        }

    print(colored(summary["file_path"], "green"))
    print(summary["summary"])
    print("-" * 80 + "\n")
    return summary


def summarize_image_document_sync(doc: ImageDocument):
    client = ollama.Client()
    response = client.chat(
        model="moondream",
        messages=[
            {"role": "user", "content": "Summarize the contents of this image.", "images": [doc.image_path]}
        ],
        options={"num_predict": 128}
    )

    summary = {
        "file_path": doc.image_path,
        "summary": response["message"]["content"],
    }

    print(colored(summary["file_path"], "green"))
    print(summary["summary"])
    print("-" * 80 + "\n")
    return summary
