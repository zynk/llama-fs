import json
import os
import pathlib
import queue
from pathlib import Path
from typing import Optional
import shutil

import colorama
import ollama
from asciitree import LeftAligned
from asciitree.drawing import BOX_LIGHT, BoxStyle
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import SimpleDirectoryReader
from pydantic import BaseModel
from termcolor import colored
from watchdog.observers import Observer

from src.loader import get_dir_summaries
from src.tree_generator import create_file_tree
from src.watch_utils import Handler
from src.watch_utils import create_file_tree as create_watch_file_tree

from dotenv import load_dotenv
load_dotenv()

class Request(BaseModel):
    path: Optional[str] = None
    instruction: Optional[str] = None
    incognito: Optional[bool] = False


class CommitRequest(BaseModel):
    base_path: str
    src_path: str  # Relative to base_path
    dst_path: str  # Relative to base_path


app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/batch")
async def batch(request: Request):
    path = request.path
    if not os.path.exists(path):
        raise HTTPException(
            status_code=400, detail="Path does not exist in filesystem"
        )

    summaries = await get_dir_summaries(path)
    files = create_file_tree(summaries)

    # Build directory tree (for preview/log)
    tree = {}
    for file in files:
        parts = Path(file["dst_path"]).parts
        current = tree
        for part in parts:
            current = current.setdefault(part, {})
    tree = {path: tree}
    tr = LeftAligned(draw=BoxStyle(gfx=BOX_LIGHT, horiz_len=1))
    print(tr(tree))

    # Attach summaries to response
    for file in files:
        file["summary"] = summaries[files.index(file)]["summary"]

    return files


@app.post("/watch")
async def watch(request: Request):
    path = request.path
    if not os.path.exists(path):
        raise HTTPException(
            status_code=400, detail="Path does not exist in filesystem"
        )

    response_queue = queue.Queue()
    observer = Observer()
    event_handler = Handler(path, create_watch_file_tree, response_queue)
    await event_handler.set_summaries()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    def stream():
        while True:
            response = response_queue.get()
            yield json.dumps(response) + "\n"

    return StreamingResponse(stream())


@app.post("/commit")
async def commit(request: CommitRequest):
    print('*' * 80)
    print("Committing file move:")
    print(f"Base path: {request.base_path}")
    print(f"Source: {request.src_path}")
    print(f"Destination: {request.dst_path}")
    print('*' * 80)

    src = os.path.join(request.base_path, request.src_path)
    dst = os.path.join(request.base_path, request.dst_path)

    if not os.path.exists(src):
        raise HTTPException(
            status_code=400, detail="Source path does not exist in filesystem"
        )

    dst_directory = os.path.dirname(dst)
    os.makedirs(dst_directory, exist_ok=True)

    try:
        if os.path.isfile(src) and os.path.isdir(dst):
            shutil.move(src, os.path.join(dst, os.path.basename(src)))
        else:
            shutil.move(src, dst)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while moving the resource: {e}"
        )

    return {"message": "Commit successful"}
