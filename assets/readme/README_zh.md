<p align="right">
  <a href="../../README.md">English</a> · <b>中文</b> · <a href="README_ja.md">日本語</a> · <a href="README_es.md">Español</a>
</p>

<p align="center">
  <img src="../catchme-logo.png" width="360" alt="CatchMe Logo"/>
</p>

<h1 align="center">CatchMe：捕捉你的完整数字足迹</h1>

<p align="center">
  <b>让你的 Agent 更懂你：轻量、无向量、强大。</b>
</p>

<p align="center">
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/许可证-Apache%202.0-blue?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-%E2%89%A53.11-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/平台-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat" alt="Platform">
  <a href="https://hkuds.github.io/CatchMe"><img src="https://img.shields.io/badge/博客-在线-orange?style=flat" alt="Blog"></a>
  <img src="https://img.shields.io/badge/报告-即将发布-lightgrey?style=flat" alt="Report">
  <br>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/飞书-交流群-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/微信-交流群-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/2vDYc2w5"><img src="https://img.shields.io/badge/Discord-加入-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#-核心功能">功能特性</a> &nbsp;·&nbsp;
  <a href="#%F0%9F%92%A1-catchme-%E6%9E%B6%E6%9E%84">工作原理</a> &nbsp;·&nbsp;
  <a href="#-llm-%E9%85%8D%E7%BD%AE">LLM 配置</a> &nbsp;·&nbsp;
  <a href="#-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B">快速开始</a> &nbsp;·&nbsp;
  <a href="#-%E6%88%90%E6%9C%AC%E4%B8%8E%E6%95%88%E7%8E%87">成本</a> &nbsp;·&nbsp;
  <a href="#-%E7%A4%BE%E5%8C%BA">社区</a>
</p>

<p align="center"><i>「 <b>放手去做你的事。CatchMe 会记下其余一切——本地存储，保障隐私与安全。</b> 」</i></p>

<p align="center">
  <img src="../terminal_demo.svg" alt="CatchMe 终端演示"/>
</p>

**🦞 让你的 Agent 真正个性化**。CatchMe 以兼容 CLI Agent（OpenClaw、NanoBot、Claude、Cursor 等）的 Skill 形式发布。你可独立运行 CatchMe；Agent 仅通过 CLI 命令查询记忆。

## 🎯 丰富你的个人数字语境

<table width="100%">
  <tr>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_coding.png" height="150" alt="编程"/><br>
      <h3>💻 个人编程助手</h3>
      <b><i>「我今天在 Claude Code 里写了什么？」</i></b><br><br>
      <div align="left">
        • 代码会话回放<br>
        • 回忆编辑过的文件<br>
        • 追溯输入内容
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_research.png" height="150" alt="研究"/><br>
      <h3>🔍 个人深度研究</h3>
      <b><i>「我昨天在读哪些 AI 相关内容？」</i></b><br><br>
      <div align="left">
        • 浏览过的网页/PDF<br>
        • 输入的搜索查询<br>
        • 阅读信息被跟踪记录
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_files.png" height="150" alt="文件"/><br>
      <h3>📁 个人文件管理</h3>
      <b><i>「我今天改过哪些文件？」</i></b><br><br>
      <div align="left">
        • 文件变更被跟踪<br>
        • 访问过的文档<br>
        • 编辑可被回顾
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_digital_life.png" height="150" alt="数字生活"/><br>
      <h3>🧩 数字生活总览</h3>
      <b><i>「我这个下午是怎么过的？」</i></b><br><br>
      <div align="left">
        • 应用使用被跟踪<br>
        • 工作流可回放<br>
        • 活动可被回忆
      </div>
    </td>
  </tr>
</table>

## ✨ 核心功能

### 📹 全时事件采集
- **事件驱动录制**：无定时器、无延迟——即时捕获带十字标注的鼠标操作。
- **全面上下文**：五路录制器围绕鼠标操作，跟踪窗口、键盘、剪贴板、通知与文件。

### 🌲 智能记忆层级
- **自动整理**：原始流自动组织为五级：日 → 会话 → 应用 → 位置 → 操作。
- **智能摘要**：各层级由 LLM 生成摘要，将日志转化为可检索的知识树。

### 🔍 基于树的检索
- **无向量复杂度**：跳过 Embedding 与向量库（VDB）——系统采用基于树的推理进行导航。
- **自顶向下搜索**：LLM 阅读摘要、选择相关分支并下钻到证据。

### 🤖 零配置 Agent 集成
- **单文件接入**：将单个 Skill 文件放入任意 AI Agent 即可集成。
- **即时访问**：基于 CLI 的屏幕历史查询，无需额外配置。

### 🪶 极轻量且隐私优先
- **占用极小**：运行时约 0.2GB 内存，SQLite + FTS5 高效存储。
- **本地与离线**：数据留在本机；通过 Ollama / vLLM / LM Studio 可完全离线。

### 🖥️ 丰富的 Web 界面
- **可视化探索**：交互式时间线、记忆树导航与实时系统监控。
- **自然对话**：用自然语言与你的完整数字足迹对话。

<p align="center">
  <img src="../web.png" width="100%" alt="CatchMe Web 面板"/>
</p>


## 💡 CatchMe 架构

CatchMe 通过三个并发阶段，将原始数字活动转化为可检索的结构化记忆：

### 🔄 录制 → 整理 → 推理：把数字混沌变成可查询的记忆

**采集**。六路后台录制器静默跟踪你的活动：窗口焦点、按键、鼠标移动、截图、剪贴板与通知。

**索引**。原始事件自动组织为**层级活动树**：日 → 会话 → 应用 → 位置 → 操作。每个节点都有 LLM 生成的摘要；无需向量 Embedding 也能快速、有意义地回忆。

**检索**。你提出问题，LLM 自顶向下遍历记忆树，选取相关节点并查看截图、按键等原始数据，然后合成精确答案。

<p align="center">
  <img src="../catchme-pipe.png" width="680" alt="CatchMe 流程：采集 → 索引 → 检索"/>
</p>

### 🌲 层级活动树
活动树是 CatchMe 记忆的核心，以结构化、多层级方式呈现你的数字生活——既可浏览高层摘要，也可下钻到细节。

<p align="center">
  <img src="../fig1_activity_tree.png" width="800" alt="层级活动树结构"/>
</p>

### 🔍 智能树检索
CatchMe 跳过传统向量检索，改由 LLM 直接导航活动树，支持跨日期的复杂推理，并从原始活动历史中精准取证。

<p align="center">
  <img src="../fig2_retrieval.png" width="800" alt="基于树的检索过程"/>
</p>

**📖 延伸阅读**：设计与技术细节见我们的[博客](https://hkuds.github.io/CatchMe)。

## 🧠 LLM 配置

### **❗️ 数据隐私说明**
• **100% 本地存储**：所有原始数据（截图、按键、活动树）保存在 `~/data/`，不会离开你的机器。

• **离线优先**：本地 LLM（Ollama、vLLM、LM Studio）可完全离线运行，不依赖云端。

• **⚠️ 云端服务商注意**：若使用云端 API，将用你的日常活动生成摘要。**不可信的接口可能泄露隐私数据**——请仔细阅读服务商的数据政策。

### **📋 要求**
• **多模态**：模型需能处理文本 + 图像。

• **上下文窗口**：确保模型的上下文长度大于 `config.json` 中的 `max_tokens` 限制。

• **成本控制**：若需**强制控制成本**，可通过 `llm.max_calls` 设限，或增大 `filter.mouse_cluster_gap` 以降低摘要频率。

CatchMe 需要 LLM 进行后台摘要与智能检索。使用 **catchme init**（见<a href="#-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B">快速开始</a>）进行**引导式配置**，或按下方**手动配置**。

云端 API 示例：

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

本地/离线示例：

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
<summary><b>支持的 LLM 服务商</b></summary>

| 服务商                     | 配置名称                   | 默认 API 地址                                           | 获取密钥                                                             |
| ------------------------- | ------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------- |
| **OpenRouter**（聚合网关）  | `openrouter`             | `https://openrouter.ai/api/v1`                          | [openrouter.ai/keys](https://openrouter.ai/keys)                     |
| **Requesty**（聚合网关）    | `requesty`               | `https://router.requesty.ai/v1`                         | [app.requesty.ai/api-keys](https://app.requesty.ai/api-keys)         |
| **AiHubMix**（聚合网关）   | `aihubmix`               | `https://aihubmix.com/v1`                               | [aihubmix.com](https://aihubmix.com)                                 |
| **硅基流动**（聚合网关）    | `siliconflow`            | `https://api.siliconflow.cn/v1`                         | [cloud.siliconflow.cn](https://cloud.siliconflow.cn)                 |
| **OpenAI**                | `openai`                 | `https://api.openai.com/v1`                             | [platform.openai.com](https://platform.openai.com/api-keys)          |
| **Anthropic**             | `anthropic`              | `https://api.anthropic.com/v1`                          | [console.anthropic.com](https://console.anthropic.com)               |
| **DeepSeek**              | `deepseek`               | `https://api.deepseek.com/v1`                           | [platform.deepseek.com](https://platform.deepseek.com/api_keys)      |
| **Gemini**                | `gemini`                 | `https://generativelanguage.googleapis.com/v1beta`      | [aistudio.google.com](https://aistudio.google.com/apikey)            |
| **Groq**                  | `groq`                   | `https://api.groq.com/openai/v1`                        | [console.groq.com](https://console.groq.com/keys)                    |
| **Mistral**               | `mistral`                | `https://api.mistral.ai/v1`                             | [console.mistral.ai](https://console.mistral.ai)                     |
| **Moonshot / Kimi**       | `moonshot`               | `https://api.moonshot.ai/v1`                            | [platform.moonshot.cn](https://platform.moonshot.cn)                 |
| **MiniMax**               | `minimax`                | `https://api.minimax.io/v1`                             | [platform.minimaxi.com](https://platform.minimaxi.com)               |
| **智谱 AI（GLM）**         | `zhipu`                  | `https://open.bigmodel.cn/api/paas/v4`                  | [open.bigmodel.cn](https://open.bigmodel.cn)                         |
| **阿里云百炼（Qwen）**      | `dashscope`              | `https://dashscope.aliyuncs.com/compatible-mode/v1`     | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| **火山引擎**               | `volcengine`             | `https://ark.cn-beijing.volces.com/api/v3`              | [console.volcengine.com](https://console.volcengine.com)             |
| **火山引擎 Coding**        | `volcengine_coding_plan` | `https://ark.cn-beijing.volces.com/api/coding/v3`       | [console.volcengine.com](https://console.volcengine.com)             |
| **BytePlus**              | `byteplus`               | `https://ark.ap-southeast.bytepluses.com/api/v3`        | [console.byteplus.com](https://console.byteplus.com)                 |
| **BytePlus Coding**       | `byteplus_coding_plan`   | `https://ark.ap-southeast.bytepluses.com/api/coding/v3` | [console.byteplus.com](https://console.byteplus.com)                 |
| **Ollama**（本地）         | `ollama`                 | `http://localhost:11434/v1`                             | —                                                                    |
| **vLLM**（本地）           | `vllm`                   | `http://localhost:8000/v1`                              | —                                                                    |
| **LM Studio**（本地）      | `lmstudio`               | `http://localhost:1234/v1`                              | —                                                                    |

> 任何兼容 OpenAI 协议的接口均可使用——直接设置 `api_url` 和 `api_key` 即可。

</details>

<details>
<summary><b>全部配置参数</b></summary>

| 模块           | 参数                       | 默认值      | 说明                                           |
| ------------- | -------------------------- | ----------- | ---------------------------------------------- |
| **web**       | `host`                     | `127.0.0.1` | 面板监听地址                                    |
|               | `port`                     | `8765`      | 面板端口                                        |
| **llm**       | `provider`                 | —           | LLM 服务商名称（见上表）                         |
|               | `api_key`                  | —           | 服务商 API 密钥                                 |
|               | `api_url`                  | *(自动)*    | 自定义接口地址，省略时按服务商自动设置             |
|               | `model`                    | —           | 模型名称（因服务商而异）                          |
|               | `wire_api`                 | *(省略)*    | 设为 `"responses"` 可对接只暴露 `POST /v1/responses` 的服务商 |
|               | `max_calls`                | `0`         | 每轮最大 LLM 调用次数（`0` = 不限制；可设上限以控制成本） |
|               | `max_images_per_cluster`   | `5`         | 每个事件簇发送的最大截图数量                      |
| **filter**    | `window_min_dwell`         | `3.0`       | 窗口最短停留时间（秒），低于此值不记录            |
|               | `keyboard_cluster_gap`     | `3.0`       | 键盘事件聚合间隔（秒）                           |
|               | `mouse_cluster_gap`        | `3.0`       | 合并鼠标事件的时间间隔（秒）；**数值越大，LLM 摘要越少** |
| **summarize** | `language`                 | `en`        | 摘要输出语言（`en`、`zh` 等）                   |
|               | `max_tokens_l0`–`l3`       | `1200`      | 各树层最大 token 数（L0=操作 … L3=会话）        |
|               | `temperature`              | `0.4`       | 摘要 LLM 温度参数                               |
|               | `max_workers`              | `2`         | 并发摘要工作线程数                               |
|               | `debounce_sec`             | `3.0`       | 触发摘要前的防抖延迟（秒）                       |
|               | `save_interval_sec`        | `5.0`       | 活动树自动保存间隔（秒）                         |
| **retrieve**  | `max_prompt_chars`         | `42000`     | 检索提示词最大字符数                             |
|               | `max_iterations`           | `15`        | 树遍历最大迭代次数                               |
|               | `max_file_chars`           | `8000`      | 提取文件内容最大字符数                           |
|               | `max_select_nodes`         | `7`         | 每次迭代最多选取节点数                           |
|               | `max_tokens_step`          | `4096`      | 每步检索最大 token 数                           |
|               | `max_tokens_answer`        | `8192`      | 最终答案最大 token 数                           |
|               | `temperature_select`       | `0.3`       | 节点选择温度参数                                |
|               | `temperature_answer`       | `0.5`       | 答案生成温度参数                                |
|               | `temperature_time_resolve` | `0.1`       | 时间解析温度参数                                |
|               | `max_tokens_time_resolve`  | `1000`      | 时间解析最大 token 数                           |

</details>

## 🚀 快速开始

### 📦 安装

```bash
git clone https://github.com/HKUDS/catchme.git && cd catchme

conda create -n catchme python=3.11 -y && conda activate catchme

pip install -e .
```

> **macOS** — 在「系统设置 → 隐私与安全性」中授予 *辅助功能*、*输入监控*、*屏幕录制* 权限  
> **Windows** — 以管理员身份运行，以启用全局输入监控

### ⚡ 初始化

```bash
catchme init                  # 交互式配置：服务商、API Key、模型
```

### 🔥 运行

```bash
catchme awake                 # 开始录制
catchme web                   # 可视化与对话

# 或通过 CLI
catchme ask -- "我今天都做了什么？"
```

<details>
<summary><b>完整 CLI 命令参考</b></summary>

| 命令                        | 说明                                                   |
| --------------------------- | ------------------------------------------------------ |
| `catchme awake`             | 启动后台录制守护进程                                    |
| `catchme web [-p PORT]`     | 启动 Web 面板（默认 `http://127.0.0.1:8765`）           |
| `catchme ask -- "问题"`     | 用自然语言查询活动历史                                  |
| `catchme cost`              | 查看 LLM Token 用量（最近 10 分钟 / 今日 / 累计）       |
| `catchme disk`              | 查看存储用量与事件数量统计                               |
| `catchme ram`               | 查看运行进程的内存占用                                  |
| `catchme init`              | 交互式配置：LLM 服务商、API Key 与模型                  |

</details>


## 🦞 CatchMe 让你的 Agent 真正个性化

CatchMe 以兼容 CLI Agent（OpenClaw、NanoBot、Claude、Cursor 等）的 Skill 形式发布。

**🪶 Agent 集成：**  
自行运行 CatchMe；Agent 仅通过 CLI 命令查询记忆。

```bash
# 1. 自行启动 CatchMe
catchme awake

# 2. 将轻量 Skill 交给你的 Agent
cp CATCHME-light.md ~/.cursor/skills/catchme/SKILL.md
```

**方案 B — 完整 Skill**（由 Agent 自主管理 CatchMe 全生命周期）：

```bash
cp CATCHME-full.md ~/.cursor/skills/catchme/SKILL.md
```

### 🔧 接入当前工作流

```python
from catchme import CatchMe
from catchme.pipelines.retrieve import retrieve

# 1. 一行搜索 — 全量活动上的快速关键词查找
with CatchMe() as mem:
    for e in mem.search("会议记录"):
        print(e.timestamp, e.data)

# 2. LLM 检索 — 针对屏幕历史的自然语言问答
for step in retrieve("我今天上午在做什么？"):
    if step["type"] == "answer":
        print(step["content"])
```

## 📊 成本与效率

*基准：**MacBook Air M4 上连续 2 小时高强度使用***


| 指标                                    | 数值                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| **运行时内存**                           | 约 0.2 GB                                                                    |
| **磁盘占用**                             | 约 200 MB                                                                       |
| **Token 吞吐**                          | 输入约 6 M，输出约 0.7 M                                                     |
| **LLM 费用** — `qwen-3.5-plus`          | 约 $0.42（[阿里云百炼](https://home.console.aliyun.com/home/dashboard/)）  |
| **LLM 费用** — `gemini-3-flash-preview` | 约 $5.00（[OpenRouter](https://openrouter.ai/models)）                     |
| **完整检索速度**（视问题而定）          | 使用 `gemini-3-flash-preview` 每次查询约 5–20 秒                                |


## 🚀 路线图

CatchMe 随社区反馈演进，规划中的能力包括：

**多设备录制**。通过局域网同步，采集并统一多台机器上的 GUI 活动。

**动态聚类**。自适应聚类，更贴近真实工作流与操作节奏，并降低不必要的成本。

**更强数据利用**。在现有流水线之外，进一步从截图与元数据中挖掘更深洞察。

> 🌟 **Star 本仓库**以关注更新——你的支持是我们持续迭代的动力！

欢迎各类贡献：评论、Bug 反馈、功能想法或 Pull Request。详见 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

## 🤝 社区

### 致谢！

CatchMe 受到这些优秀开源项目的启发：

| 项目                                                            | 启发来源                                  |
| --------------------------------------------------------------- | ----------------------------------------- |
| [ActivityWatch](https://github.com/ActivityWatch/activitywatch) | 开源活动追踪领域的先驱                     |
| [Screenpipe](https://github.com/mediar-ai/screenpipe)           | 面向 AI Agent 的屏幕录制基础设施           |
| [Windrecorder](https://github.com/Antonoko/Windrecorder)        | Windows 端个人屏幕录制与搜索               |
| [OpenRecall](https://github.com/openrecall/openrecall)          | Windows Recall 的开源替代方案             |
| [Selfspy](https://github.com/selfspy/selfspy)                   | 经典守护进程风格的活动日志工具             |
| [PageIndex](https://github.com/HKUDS/PageIndex)                 | 无需 Embedding 的树状文档检索              |
| [MineContext](https://github.com/volcengine/MineContext)        | 主动式上下文感知 AI 伙伴与屏幕语境采集        |


### 🏛️ 生态系统

CatchMe 是 **[HKUDS](https://github.com/HKUDS)** Agent 生态的一部分——构建个人 AI Agent 的基础设施层：

<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>超轻量个人 AI 助手</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>让所有软件具备 Agent 原生能力</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawWork"><b>ClawWork</b></a><br>
      <sub>从 AI 助手到 AI 协作者的演进</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>面向全流程自动化的 Agent 群体智能</sub>
    </td>
  </tr>
</table>
<br>
<p align="center">
  感谢访问 ✨ <b>CatchMe</b>
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.catchme" alt="visitors"/>
</p>
