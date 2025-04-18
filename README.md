# LlamaFS

<img src="electron-react-app/assets/llama_fs.png" width="30%" />

## Ollama Updation

Okay, so I really bastardized this project to use Ollama instead of Groq, delete all Groq code, use this at your own risk. I only cared about the folder organization, renaming files wasn't really important to me but I added that in anyway.

Feel free to mess with the actual prompt located in src\tree_generator.py and watch_utils, snippet is called "File_Prompt", it's highly effective to just change what you're asking it rather than the code itself.

Utilizes Ollama, completely local, codellama:instruct is the model, mainly because it has no ethical dilemmas with images you feed it. No need for icognito toggle, overkill.

You will need to install the ollama dependencies below. The requirements has been updated per my changes.

I got rid of AgentOps, it's fast enough, we get it. I trashed all the other bs, just install requirements, install ollama dependencies, and run it with the command at the end. Done.

## Inspiration

Open your `~/Downloads` directory. Or your Desktop. It's probably a mess...

> There are only two hard things in Computer Science: cache invalidation and **naming things**.

## What it does

LlamaFS is a self-organizing file manager. It automatically renames and organizes your files based on their content and well-known conventions (e.g., time). It supports many kinds of files, including images (through Moondream) and audio (through Whisper).

LlamaFS runs in two "modes" - as a batch job (batch mode), and an interactive daemon (watch mode).

In batch mode, you can send a directory to LlamaFS, and it will return a suggested file structure and organize your files.

In watch mode, LlamaFS starts a daemon that watches your directory. It intercepts all filesystem operations and uses your most recent edits to proactively learn how you rename file. For example, if you create a folder for your 2023 tax documents, and start moving 1-3 files in it, LlamaFS will automatically create and move the files for you!

Uh... Sending all my personal files to an API provider?! No thank you!

~~It also has a toggle for "incognito mode," allowing you route every request through Ollama instead of Groq. Since they use the same Llama 3 model, the perform identically.~~

## How we built it

We built LlamaFS on a Python backend, leveraging the Llama3 model through Groq for file content summarization and tree structuring. For local processing, we integrated Ollama running the same model to ensure privacy in incognito mode. The frontend is crafted with Electron, providing a sleek, user-friendly interface that allows users to interact with the suggested file structures before finalizing changes.

- **It's extremely fast!** (by LLM standards)! Most file operations are processed in <500ms in watch mode ~~(benchmarked by [AgentOps](https://agentops.ai/?utm_source=llama-fs))~~. This is because of our smart caching that selectively rewrites sections of the index based on the minimum necessary filesystem diff. ~~And of course, Groq's super fast inference API. 😉~~ (This was written by AI, can you tell?)

- **It's immediately useful** - It's very low friction to use and addresses a problem almost everyone has. We started using it ourselves on this project (very Meta).

## What's next for LlamaFS

- Find and remove old/unused files
- We have some really cool ideas for - filesystem diffs are hard...

## Installation

### Prerequisites

Before installing, ensure you have the following requirements:
- Python 3.10 or higher
- pip (Python package installer)

### Installing

To install the project, follow these steps:
1. Clone the repository:
   ```bash
   git clone https://github.com/zynk/llama-fs.git
   ```

2. Navigate to the project directory:
    ```bash
    cd llama-fs
    ```

3. Install requirements
   ```bash
   pip install -r requirements.txt
   ```
I already included other shit you will most likely need.

~~4. Update your `.env`~~
~~Copy `.env.example` into a new file called `.env`. Then, provide the following API keys:~~
~~* Groq: You can obtain one from [here](https://console.groq.com/keys).~~
~~* AgentOps: You can obtain one from [here](https://app.agentops.ai/settings/projects).~~ (Ew.)

~~Groq is used for fast cloud inference but can be replaced with Ollama in the code directly (TODO.~~ Not.)

~~AgentOps is used for logging and monitoring and will report the latency, cost per session, and give you a full session replay of each LlamaFS call.~~ (Hell no.)

5. (Not Optional) Install moondream if you want to use the incognito mode
    ```bash
    ollama pull moondream
    ollama pull codellama:instruct
    ```

## Usage

To serve the application locally using FastAPI, run the following command
   ```bash
   fastapi dev server.py
   ```

This will run the server by default on port 8000. The API can be queried using a `curl` command, and passing in the file path as the argument. For example, on the Downloads folder:
   ```bash
   curl -X POST http://127.0.0.1:8000/batch \
    -H "Content-Type: application/json" \
    -d '{"path": "/Users/<username>/Downloads/", "instruction": "string", "incognito": false}'
   ```

The above bash is for development.. just use this command:
   ```bash
   python main.py "C:/Users/<username>/Downloads" "C:/Users/<username>/Organized" --auto-yes
   ```

If you want to move the files (not copy) just add in --move
   ```bash
   python main.py "C:/Users/<username>/Downloads" "C:/Users/<username>/Organized" --move --auto-yes
   ```
