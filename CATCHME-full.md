---
name: catchme
description: >-
  Install, configure, and operate the catchme always-on screen recorder.
  Use when the user mentions catchme, activity recording, screen capture,
  digital footprint, or needs to query what they were doing/seeing earlier.
---

# CatchMe — Full Setup & Operation

CatchMe captures screen activity (keystrokes, window switches, mouse, clipboard, screenshots), organizes events into a hierarchical memory tree with LLM summaries, and answers natural-language queries about the user's history. All data stays local.

Follow the steps below **in order**. Each step has a verification check — only proceed when it passes.

---

## Step 0 · Already installed?

Find the conda env that has catchme (the env name is user-defined, not necessarily `catchme`):

```bash
find "$(conda info --base)/envs" -path "*/bin/catchme" 2>/dev/null | head -1
```

- If this prints a path like `.../envs/ENVNAME/bin/catchme` → catchme is installed. Activate that env: `conda activate ENVNAME`, then run `catchme ram`.
- If this prints nothing → not installed. Go to **Step 1**.

| `catchme ram` result | Meaning | Go to |
|----------------------|---------|-------|
| Shows `awake` process | Installed and recording | → **Usage** |
| Runs but no processes listed | Installed, not recording | → **Step 4** |

---

## Step 1 · Clone & install

```bash
git clone https://github.com/HKUDS/catchme.git
cd catchme
conda create -n catchme python=3.11 -y
conda activate catchme
pip install -e .
```

**Verify:** `which catchme` prints a path inside the conda env.

---

## Step 2 · Configure

> `catchme init` is interactive (uses stdin prompts) and **cannot be scripted**. Write the config file directly instead.

First, find the config path:

```bash
python -c "from catchme.config import get_default_config; print(get_default_config().config_path)"
```

By default this is `~/.catchme/config.json` (or `%USERPROFILE%\.catchme\config.json` on Windows). Use the printed path if the config root has been customized.

**Ask the user** for their LLM provider and API key, then write the config:

```json
{
    "llm": {
        "provider": "<PROVIDER>",
        "api_key": "<KEY>",
        "model": "<MODEL>"
    }
}
```

**Privacy:** When a cloud provider is configured, CatchMe sends activity-derived text and selected screenshots to that endpoint for summarization and retrieval. For offline processing, use an on-device provider and endpoint; custom API URLs may still point to a remote service.

Recommended defaults per provider:

| Provider | `provider` value | Default `model` | Needs `api_key`? |
|----------|-----------------|-----------------|-----------------|
| OpenRouter | `openrouter` | `google/gemini-3-flash-preview` | Yes |
| OpenAI | `openai` | `gpt-4o-mini` | Yes |
| Anthropic | `anthropic` | `claude-sonnet-4-20250514` | Yes |
| DeepSeek | `deepseek` | `deepseek-chat` | Yes |
| Gemini | `gemini` | `gemini-2.5-flash` | Yes |
| DashScope | `dashscope` | `qwen-plus` | Yes |
| Ollama (local) | `ollama` | `llama3` | No |
| vLLM (local) | `vllm` | `llama3` | No |

**Verify:** `python -c "from catchme.services import load_config; c=load_config(reload=True); print(c['llm']['provider'], c['llm']['model'])"` prints the provider and model you set.

---

## Step 3 · permissions

The user must manually grant these in **System Settings → Privacy & Security**:

- **Accessibility**
- **Input Monitoring**
- **Screen Recording**

Tell the user to do this. The agent cannot grant permissions automatically.

---

## Step 4 · Start recording

`catchme awake` is a **long-running daemon** — run it in a dedicated background terminal:

```bash
conda activate ENVNAME && catchme awake
```

(Replace `ENVNAME` with the env name from Step 0 or Step 1.)

It will print live events to stdout. Do **not** wait for it to finish — it should always be alive, until you want to end it (by `Ctrl+C`).

**Verify** (in a separate terminal):

```bash
conda activate ENVNAME && catchme ram
```

Should show the `awake` process with PID and RAM usage.

---

## Usage

All commands require `conda activate ENVNAME` first (use the env name discovered in Step 0 or created in Step 1).

| Command | What it does |
|---------|-------------|
| `catchme ask -- "<question>"` | Natural-language query over screen history |
| `catchme web [-p PORT]` | Web dashboard (default `http://127.0.0.1:8765`) |
| `catchme cost` | Token usage: last 10 min / today / all time |
| `catchme disk` | Storage: database + screenshots + trees + event count |
| `catchme ram` | RAM usage of all catchme processes |

Example queries:

```bash
catchme ask -- "What was user working on this morning?"
catchme ask -- "When did user last open Figma?"
catchme ask -- "Summarize user's afternoon session"
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `command not found: catchme` | Wrong env or not activated — re-run `find` from Step 0 |
| `ask` returns empty / no data | `catchme awake` not running — check `catchme ram` |
| LLM errors | Verify config: `python -c "from catchme.services import load_config; print(load_config()['llm'])"` |
| No events recorded | macOS permissions not granted (Step 3) |
| Port already in use | `catchme web -p 9000` or `lsof -i :8765` |
