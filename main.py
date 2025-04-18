import os
import json
import shutil
import asyncio
import pathlib
import requests
import colorama
from pathlib import Path
from termcolor import colored
from asciitree import LeftAligned
from asciitree.drawing import BoxStyle, BOX_LIGHT
from dotenv import load_dotenv
import click

from src.loader import get_dir_summaries
from src.tree_generator import create_file_tree

load_dotenv()
colorama.init()  # Enables ANSI coloring on Windows terminals


@click.command()
@click.argument("src_path", type=click.Path(exists=True))
@click.argument("dst_path", type=click.Path())
@click.option("--auto-yes", is_flag=True, help="Automatically say yes to all prompts")
@click.option("--move", is_flag=True, help="Move files instead of copying")
def main(src_path, dst_path, auto_yes=False, move=False):
    src_path = Path(src_path)
    dst_path = Path(dst_path)
    dst_path.mkdir(exist_ok=True)

    # 1. Get summaries
    summaries = asyncio.run(get_dir_summaries(str(src_path)))

    # 2. Generate structured file tree
    files = create_file_tree(summaries)

    # 3. Build and preview ASCII folder tree
    tree = {}
    for file in files:
        parts = Path(file["dst_path"]).parts
        current = tree
        for part in parts:
            current = current.setdefault(part, {})
    tree = {str(dst_path): tree}
    tr = LeftAligned(draw=BoxStyle(gfx=BOX_LIGHT, horiz_len=1))
    print(tr(tree))

    # 4. Normalize src and dst paths
    for file in files:
        # Use model's relative dst_path to create full destination path
        file["dst_path"] = dst_path / Path(file["dst_path"])
        file["src_path"] = src_path / Path(file["src_path"]).name

    # 5. Confirm with user
    if not auto_yes and not click.confirm("Proceed with directory structure?", default=True):
        click.echo("Operation cancelled.")
        return

    # 6. Move or copy files
    for file in files:
        src_file = file["src_path"]
        dst_file = file["dst_path"]

        dst_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if move:
                shutil.move(str(src_file), str(dst_file))
                print(f"🚚 Moved: {src_file} → {dst_file}")
            else:
                shutil.copy2(str(src_file), str(dst_file))
                print(f"📁 Copied: {src_file} → {dst_file}")
        except Exception as e:
            print(f"❌ Failed to transfer {src_file}: {e}")


if __name__ == "__main__":
    main()
