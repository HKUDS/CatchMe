<p align="right">
  <a href="assets/readme/README_zh.md">中文</a> · <a href="assets/readme/README_ja.md">日本語</a> · <a href="assets/readme/README_es.md">Español</a> · <b>English</b>
</p>

<p align="center">
  <img src="assets/catchme-logo.png" width="360" alt="CatchMe Logo"/>
</p>

<h1 align="center">CatchMe: Make Your AI Agents Truly Personal</h1>

<p align="center">
  <b>Capture Your Entire Digital Footprint: Lightweight & Vectorless & Powerful.</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-%E2%89%A53.11-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat" alt="Platform">
  <a href="https://hkuds.github.io/CatchMe"><img src="https://img.shields.io/badge/Blog-online-orange?style=flat" alt="Blog"></a>
  <img src="https://img.shields.io/badge/Report-coming%20soon-lightgrey?style=flat" alt="Report">
  <br>
  <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/2vDYc2w5"><img src="https://img.shields.io/badge/Discord-Join-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#-key-features">Features</a> &nbsp;·&nbsp;
  <a href="#%EF%B8%8F-how-it-works">How It Works</a> &nbsp;·&nbsp;
  <a href="#-llm-configuration">LLM Config</a> &nbsp;·&nbsp;
  <a href="#-get-started">Get Started</a> &nbsp;·&nbsp;
  <a href="#-cost--efficiency">Cost</a> &nbsp;·&nbsp;
  <a href="#-community">Community</a>
</p>

<p align="center"><i>「 <b>Just do your thing. CatchMe captures everything else — stored locally to ensure privacy and security. </b> 」</i></p>

<p align="center">
  <img src="assets/terminal_demo.svg" alt="CatchMe Terminal Demo"/>
</p>

**🦞 Makes Your Agents Truly Personal**. CatchMe ships as an agent-compatible skill for CLI agents (OpenClaw, NanoBot, Claude, Cursor, etc.). Run CatchMe independently. Your agents query memories via CLI commands only.
##


## 🎯 Enrich Your Personal Digital Context

<table width="100%">
  <tr>
    <td align="center" width="25%" valign="top">
      <img src="assets/usecase_coding.png" height="150" alt="Coding"/><br>
      <h3>💻 Personal Coding Assistant</h3>
      <b><i>"What was I coding in Claude Code today?"</i></b><br><br>
      <div align="left">
        • Code session replay<br>
        • Recall your edited files<br>
        • Trace what you typed
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/usecase_research.png" height="150" alt="Research"/><br>
      <h3>🔍 Personal Deep Research</h3>
      <b><i>"What was I reading about AI yesterday?"</i></b><br><br>
      <div align="left">
        • Web/PDF viewed<br>
        • Search queries typed<br>
        • Reading info tracked
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/usecase_files.png" height="150" alt="Files"/><br>
      <h3>📁 Personal Files Manager</h3>
      <b><i>"Which files did I change today?"</i></b><br><br>
      <div align="left">
        • File changes tracked<br>
        • Docs accessed<br>
        • Edits reviewed
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="assets/usecase_digital_life.png" height="150" alt="Digital Life"/><br>
      <h3>🧩 Digital Life Overview</h3>
      <b><i>"How did I spend my afternoon?"</i></b><br><br>
      <div align="left">
        • App usage tracked<br>
        • Workflows replayed<br>
        • Activities recalled
      </div>
    </td>
  </tr>
</table>

## ✨ Key Features

### 📹 Always-On Event Capture
- **Event-Driven Recording**: No timer or delays - catch mouse actions with crosshair annotation instantly.
- **Comprehensive Context**: Five recorders track windows, keyboard, clipboard, notifications, and files around mouse actions.

### 🌲 Intelligent Memory Hierarchy
- **Auto-Organization**: Raw streams structure into five tiers: Day → Session → App → Location → Action.
- **Smart Summaries**: LLM summaries at each level, transforming logs into searchable knowledge trees.

### 🔍 Tree-Based Retrieval
- **No Vector Complexity**: Skip embeddings and VDBs — our system uses tree-based reasoning for navigation.
- **Top-Down Search**: LLM reads summaries, selects relevant branches, and drills down to evidence.

### 🤖 Zero-Config Agent Integration
- **One-File Setup**: Drop a single skill file into any AI agent for instant integration.
- **Immediate Access**: CLI-based screen history queries with zero configuration required.

### 🪶 Ultralight & Privacy-First
- **Minimal Footprint**: ~0.2GB runtime RAM with efficient SQLite + FTS5 storage.
- **Local & Offline**: All data stays on your machine with full offline mode via Ollama/vLLM/LM Studio.

### 🖥️ Rich Web Interface
- **Visual Exploration**: Interactive timelines, memory tree navigation, and real-time system monitoring.
- **Natural Conversation**: Chat with your complete digital footprint using natural language.

<p align="center">
  <img src="assets/web.png" width="100%" alt="CatchMe Web Dashboard"/>
</p>


## 💡 CatchMe Architecture

CatchMe transforms raw digital activity into structured, searchable memory through three concurrent stages:

### 🔄 Record → Organize → Reason: Turn digital chaos into queryable memory

**Capture**. Six background recorders silently track your activity. They monitor window focus, keystrokes, mouse movement, screenshots, clipboard, and notifications.

**Index**. Raw events auto-organize into a Hierarchical Activity Tree: Day → Session → App → Location → Action. Each node gets LLM-generated summaries. Fast, meaningful recall without vector embeddings.

**Retrieve**. You ask a question. The LLM traverses your memory tree top-down. It selects relevant nodes and inspects raw data like screenshots or keystrokes. Then synthesizes a precise answer.

<p align="center">
  <img src="assets/catchme-pipe.png" width="680" alt="CatchMe Pipeline: Capturing → Indexing → Retrieving"/>
</p>

### 🌲 Hierarchical Activity Tree
The Activity Tree is CatchMe's memory core. It provides structured, multi-level views of your digital life. Browse high-level summaries or dive into granular details.

<p align="center">
  <img src="assets/fig1_activity_tree.png" width="800" alt="Hierarchical Activity Tree Structure"/>
</p>

### 🔍 Intelligent Tree Retrieval
CatchMe skips traditional vector search. Instead, the LLM directly navigates your Activity Tree. This enables complex, cross-day reasoning. Precise evidence gathering from raw activity history.

<p align="center">
  <img src="assets/fig2_retrieval.png" width="800" alt="Tree-based Retrieval Process"/>
</p>

**📖 Learn More**: Detailed design insights and technical deep-dive available in our [blog](https://hkuds.github.io/CatchMe/).

## 🧠 LLM Configuration

### **❗️ Data Privacy Notice**
• **100% Local Storage**: All raw data (screenshots, keystrokes, activity trees) stays in ~/data/ and never leaves your machine. 

• **Offline-First Options**: Local LLMs (Ollama, vLLM, LM Studio) enable fully offline operation without any cloud dependency.

• **⚠️Cloud Provider Caution**: If used, cloud APIs will be used to summarize your daily activities. **Untrusted endpoints may expose private data** — review data policies of your provider carefully.

### **📋 Requirements**
• **Multimodal support**: Your model should be able to handle text + images.

• **Context window**: Make sure the context window of your model exceed `max_tokens` limits in `config.json`.

• **Cost control**: For *forced cost control*, set limits via `llm.max_calls` or increase `filter.mouse_cluster_gap` to reduce summarization frequency.

CatchMe requires an LLM for background summarization and intelligent retrieval. Use **catchme init** (in <a href="#-get-started">Get Started</a>)for **guided setup** or follow the **manual configuration** steps below.

For cloud API services:

```json
{
    "llm": {
        "provider": "openrouter",
        "api_key": "sk-or-...",
        "api_url": null,
        "model": "google/gemini-3-flash-preview"
    }
}
```

For local/offline operation:

```json
{
    "llm": {
        "provider": "ollama",
        "api_key": null,
        "api_url": null,
        "model": "gemma3:4b"
    }
}
```

<details>
<summary><b>Supported LLM Providers</b></summary>

| Provider                  | Config name              | Default API URL                                         | Get Key                                                              |
| ------------------------- | ------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------- |
| **OpenRouter** (gateway)  | `openrouter`             | `https://openrouter.ai/api/v1`                          | [openrouter.ai/keys](https://openrouter.ai/keys)                     |
| **AiHubMix** (gateway)    | `aihubmix`               | `https://aihubmix.com/v1`                               | [aihubmix.com](https://aihubmix.com)                                 |
| **SiliconFlow** (gateway) | `siliconflow`            | `https://api.siliconflow.cn/v1`                         | [cloud.siliconflow.cn](https://cloud.siliconflow.cn)                 |
| **OpenAI**                | `openai`                 | `https://api.openai.com/v1`                             | [platform.openai.com](https://platform.openai.com/api-keys)          |
| **Anthropic**             | `anthropic`              | `https://api.anthropic.com/v1`                          | [console.anthropic.com](https://console.anthropic.com)               |
| **DeepSeek**              | `deepseek`               | `https://api.deepseek.com/v1`                           | [platform.deepseek.com](https://platform.deepseek.com/api_keys)      |
| **Gemini**                | `gemini`                 | `https://generativelanguage.googleapis.com/v1beta`      | [aistudio.google.com](https://aistudio.google.com/apikey)            |
| **Groq**                  | `groq`                   | `https://api.groq.com/openai/v1`                        | [console.groq.com](https://console.groq.com/keys)                    |
| **Mistral**               | `mistral`                | `https://api.mistral.ai/v1`                             | [console.mistral.ai](https://console.mistral.ai)                     |
| **Moonshot / Kimi**       | `moonshot`               | `https://api.moonshot.ai/v1`                            | [platform.moonshot.cn](https://platform.moonshot.cn)                 |
| **MiniMax**               | `minimax`                | `https://api.minimax.io/v1`                             | [platform.minimaxi.com](https://platform.minimaxi.com)               |
| **Zhipu AI (GLM)**        | `zhipu`                  | `https://open.bigmodel.cn/api/paas/v4`                  | [open.bigmodel.cn](https://open.bigmodel.cn)                         |
| **DashScope (Qwen)**      | `dashscope`              | `https://dashscope.aliyuncs.com/compatible-mode/v1`     | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| **VolcEngine**            | `volcengine`             | `https://ark.cn-beijing.volces.com/api/v3`              | [console.volcengine.com](https://console.volcengine.com)             |
| **VolcEngine Coding**     | `volcengine_coding_plan` | `https://ark.cn-beijing.volces.com/api/coding/v3`       | [console.volcengine.com](https://console.volcengine.com)             |
| **BytePlus**              | `byteplus`               | `https://ark.ap-southeast.bytepluses.com/api/v3`        | [console.byteplus.com](https://console.byteplus.com)                 |
| **BytePlus Coding**       | `byteplus_coding_plan`   | `https://ark.ap-southeast.bytepluses.com/api/coding/v3` | [console.byteplus.com](https://console.byteplus.com)                 |
| **Ollama** (local)        | `ollama`                 | `http://localhost:11434/v1`                             | —                                                                    |
| **vLLM** (local)          | `vllm`                   | `http://localhost:8000/v1`                              | —                                                                    |
| **LM Studio** (local)     | `lmstudio`               | `http://localhost:1234/v1`                              | —                                                                    |

> Any OpenAI-compatible endpoint works — just set `api_url` and `api_key` directly.

</details>

<details>
<summary><b>All Configuration Parameters</b></summary>

| Section       | Parameter                  | Default     | Description                                         |
| ------------- | -------------------------- | ----------- | --------------------------------------------------- |
| **web**       | `host`                     | `127.0.0.1` | Dashboard bind address                              |
|               | `port`                     | `8765`      | Dashboard port                                      |
| **llm**       | `provider`                 | —           | LLM provider name (see table above)                 |
|               | `api_key`                  | —           | API key for the provider                            |
|               | `api_url`                  | *(auto)*    | Custom endpoint; auto-set per provider if omitted   |
|               | `model`                    | —           | Model name (provider-specific)                      |
|               | `wire_api`                 | *(omit)*    | Set to `"responses"` for providers that only expose `POST /v1/responses` instead of chat completions |
|               | `max_calls`                | `0`         | Max LLM calls per cycle (`0` = unlimited; set to limit costs) |
|               | `max_images_per_cluster`   | `5`         | Max screenshots sent per event cluster              |
| **filter**    | `window_min_dwell`         | `3.0`       | Min window dwell time (sec) before recording        |
|               | `keyboard_cluster_gap`     | `3.0`       | Keyboard event clustering gap (sec)                 |
|               | `mouse_cluster_gap`        | `3.0`       | Time gap (sec) to merge mouse events; **larger values reduce LLM summaries** |
| **summarize** | `language`                 | `en`        | Summary output language (`en`, `zh`, etc.)          |
|               | `max_tokens_l0`–`l3`       | `1200`      | Max tokens per tree level (L0=Action … L3=Session)  |
|               | `temperature`              | `0.4`       | LLM temperature for summarization                   |
|               | `max_workers`              | `2`         | Concurrent summarization workers                    |
|               | `debounce_sec`             | `3.0`       | Debounce before triggering summary                  |
|               | `save_interval_sec`        | `5.0`       | Tree auto-save interval                             |
| **retrieve**  | `max_prompt_chars`         | `42000`     | Max chars in retrieval prompt                       |
|               | `max_iterations`           | `15`        | Max tree traversal iterations                       |
|               | `max_file_chars`           | `8000`      | Max chars from extracted files                      |
|               | `max_select_nodes`         | `7`         | Max nodes selected per iteration                    |
|               | `max_tokens_step`          | `4096`      | Max tokens per retrieval step                       |
|               | `max_tokens_answer`        | `8192`      | Max tokens for final answer                         |
|               | `temperature_select`       | `0.3`       | Temperature for node selection                      |
|               | `temperature_answer`       | `0.5`       | Temperature for answer generation                   |
|               | `temperature_time_resolve` | `0.1`       | Temperature for time resolution                     |
|               | `max_tokens_time_resolve`  | `1000`      | Max tokens for time resolution                      |

</details>

## 🚀 Get Started

### 📦 Install

```bash
git clone https://github.com/HKUDS/catchme.git && cd catchme

conda create -n catchme python=3.11 -y && conda activate catchme

pip install -e .
```

> **macOS** — grant *Accessibility*, *Input Monitoring*, *Screen Recording* in System Settings → Privacy & Security
> **Windows** — run as Administrator for global input monitoring

### ⚡ Init

```bash
catchme init                  # interactive setup: provider, API key, llm model
```

### 🔥 Run

```bash
catchme awake                 # start recording
catchme web                   # visualize and chat

# or through cli
catchme ask -- "What am I doing today?"
```

<details>
<summary><b>Full CLI Reference</b></summary>

| Command                     | Description                                            |
| --------------------------- | ------------------------------------------------------ |
| `catchme awake`             | Start the recording daemon                             |
| `catchme web [-p PORT]`     | Launch web dashboard (default `http://127.0.0.1:8765`) |
| `catchme ask -- "question"` | Query your activity in natural language                |
| `catchme mcp`               | Start MCP stdio server (Claude Desktop, Cursor, …)     |
| `catchme cost`              | Show LLM token usage (last 10 min / today / all time)  |
| `catchme disk`              | Show storage breakdown & event count                   |
| `catchme ram`               | Show memory usage of running processes                 |
| `catchme init`              | Interactive setup: LLM provider, API key & model       |

</details>


## 🦞 CatchMe Makes Your Agents Truly Personal
CatchMe ships as an agent-compatible skill for CLI agents (OpenClaw, NanoBot, Claude, Cursor, etc.).

**🪶 Agent Integration:**

**Option A — Light Skill** (you run CatchMe; agents query memories via CLI commands only):

```bash
# 1. Start CatchMe yourself
catchme awake

# 2. Give the light skill to your agent
cp CATCHME-light.md ~/.cursor/skills/catchme/SKILL.md
```

**Option B — Full Skill** (agent manages the full CatchMe lifecycle autonomously):

```bash
cp CATCHME-full.md ~/.cursor/skills/catchme/SKILL.md
```

### 🔌 MCP Server

Expose your activity tree to any MCP host — Claude Desktop, Cursor, Hermes, etc. — over stdio:

```bash
pip install 'catchme[mcp]'   # MCP support ships as an optional extra
catchme mcp                  # start the stdio server
```

Register it with your host. For Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "catchme": {
      "command": "catchme",
      "args": ["mcp"]
    }
  }
}
```

Your agent then gets four tools:

| Tool                            | Description                                     |
| ------------------------------- | ----------------------------------------------- |
| `search_activity(query, date?)` | Natural-language Q&A over your screen history   |
| `list_days()`                   | All recorded days with top-level summaries      |
| `get_session(session_id)`       | Full detail for one session node                |
| `get_tree(date)`                | Raw activity tree JSON for a given date         |

> Keep `catchme awake` running — the MCP server reads the activity tree it builds.

### 🔧 Integrate into your current workflow

```python
from catchme import CatchMe
from catchme.pipelines.retrieve import retrieve

# 1. One-line search — fast keyword lookup over all recorded activity
with CatchMe() as mem:
    for e in mem.search("meeting notes"):
        print(e.timestamp, e.data)

# 2. LLM-powered retrieval — natural language Q&A over your screen history
for step in retrieve("What was I working on this morning?"):
    if step["type"] == "answer":
        print(step["content"])
```

## 📊 Cost & Efficiency

*Benchmarked with **2 hours of intensive, continuous computer use** on MacBook Air M4.*


| Metric                                          | Value                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| **Runtime RAM**                                 | ~0.2 GB                                                                    |
| **Disk Usage**                                  | ~ 200 MB                                                                        |
| **Token Throughput**                                 | input ~ 6 M , output ~ 0.7 M                                                    |                   |
| **LLM cost** — `qwen-3.5-plus`                  | ~ $0.42 via [Aliyun DashScope](https://home.console.aliyun.com/home/dashboard/) |
| **LLM cost** — `gemini-3-flash-preview`         | ~ $5.00 via [OpenRouter](https://openrouter.ai/models)       
| **Full Retrieval Speed** (depends on question) | 5 - 20s per query using `gemini-3-flash-preview`                                |


## 🚀 Roadmap
CatchMe evolves with community input. Upcoming features include:

**Multi-Device Recording**. Capture and unify GUI activities across all your machines via LAN synchronization.

**Dynamic Clustering**. Adaptive clustering algorithms that better reflect your actual work patterns and flows, reducing unnecessary costs.

**Enhanced Data Utilization**. Unlock deeper insights from screenshots and metadata beyond current processing pipelines.

> 🌟 **Star this repo** to follow our future updates — your interest keeps us motivated!

We welcome contributions of any kind - whether it's a comment, a bug report, a feature idea, or a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## 🤝 Community

### Acknowledgments !

CatchMe is inspired by these excellent open-source projects:

| Project                                                         | Inspiration                                           |
| --------------------------------------------------------------- | ----------------------------------------------------- |
| [ActivityWatch](https://github.com/ActivityWatch/activitywatch) | Pioneering open-source activity tracking              |
| [Screenpipe](https://github.com/mediar-ai/screenpipe)           | Screen recording infrastructure for AI agents         |
| [Windrecorder](https://github.com/Antonoko/Windrecorder)        | Personal screen recording & search on Windows         |
| [OpenRecall](https://github.com/openrecall/openrecall)          | Open-source alternative to Windows Recall             |
| [Selfspy](https://github.com/selfspy/selfspy)                   | Classic daemon-style activity logging                 |
| [PageIndex](https://github.com/HKUDS/PageIndex)                 | Tree-structured document retrieval without embeddings |
| [MineContext](https://github.com/volcengine/MineContext)        | Proactive context-aware AI partner & screen capture   |


### 🏛️ Ecosystem

CatchMe is part of the **[HKUDS](https://github.com/HKUDS)** agent ecosystem — building the infrastructure layer for personal AI agents:

<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>Ultra-Lightweight Personal AI Assistant</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>Making All Software Agent-Native</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawWork"><b>ClawWork</b></a><br>
      <sub>AI Assistant → AI Coworker Evolution</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>Agent Awarm Intelligence for Full Team Automation</sub>
    </td>
  </tr>
</table>
<br>
<p align="center">
  Thanks for visiting ✨ <b>CatchMe</b>
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.catchme" alt="visitors"/>
</p>
