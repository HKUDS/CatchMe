<p align="right">
  <a href="../../README.md">English</a> · <a href="README_zh.md">中文</a> · <b>日本語</b> · <a href="README_es.md">Español</a>
</p>

<p align="center">
  <img src="../catchme-logo.png" width="360" alt="CatchMe Logo"/>
</p>

<h1 align="center">CatchMe：デジタル足跡をすべて記録</h1>

<p align="center">
  <b>エージェントにもっと自分を理解させる：軽量・ベクトル不要・高機能。</b>
</p>

<p align="center">
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-%E2%89%A53.11-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat" alt="Platform">
  <a href="https://hkuds.github.io/CatchMe"><img src="https://img.shields.io/badge/Blog-online-orange?style=flat" alt="Blog"></a>
  <img src="https://img.shields.io/badge/Report-coming%20soon-lightgrey?style=flat" alt="Report">
  <br>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="../../COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/2vDYc2w5"><img src="https://img.shields.io/badge/Discord-Join-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#-主な機能">機能</a> &nbsp;·&nbsp;
  <a href="#-catchme-%E3%81%AE%E3%82%A2%E3%83%BC%E3%82%AD%E3%83%86%E3%82%AF%E3%83%81%E3%83%A3">仕組み</a> &nbsp;·&nbsp;
  <a href="#-llm%E8%A8%AD%E5%AE%9A">LLM 設定</a> &nbsp;·&nbsp;
  <a href="#-%E3%81%AF%E3%81%98%E3%82%81%E3%82%8B">はじめる</a> &nbsp;·&nbsp;
  <a href="#-%E3%82%B3%E3%82%B9%E3%83%88%E3%81%A8%E5%8A%B9%E7%8E%87">コスト</a> &nbsp;·&nbsp;
  <a href="#-%E3%82%B3%E3%83%9F%E3%83%A5%E3%83%8B%E3%83%86%E3%82%A3">コミュニティ</a>
</p>

<p align="center"><i>「 <b>あなたは作業に集中するだけ。CatchMe が残りを記録します — ローカル保存でプライバシーと安全を確保。</b> 」</i></p>

<p align="center">
  <img src="../terminal_demo.svg" alt="CatchMe ターミナルデモ"/>
</p>

**🦞 エージェントを本当にパーソナルに**。CatchMe は CLI エージェント（OpenClaw、NanoBot、Claude、Cursor など）向けの Skill として提供されます。CatchMe は単体で起動でき、エージェントは CLI コマンドだけで記憶を問い合わせます。

## 🎯 パーソナルなデジタル文脈を豊かに

<table width="100%">
  <tr>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_coding.png" height="150" alt="コーディング"/><br>
      <h3>💻 パーソナルコーディングアシスタント</h3>
      <b><i>「今日 Claude Code で何を書いていた？」</i></b><br><br>
      <div align="left">
        • コードセッションの再生<br>
        • 編集したファイルを思い出す<br>
        • 入力内容をたどる
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_research.png" height="150" alt="リサーチ"/><br>
      <h3>🔍 パーソナルディープリサーチ</h3>
      <b><i>「昨日 AI について何を読んでいた？」</i></b><br><br>
      <div align="left">
        • 閲覧した Web/PDF<br>
        • 入力した検索クエリ<br>
        • 読書情報の追跡
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_files.png" height="150" alt="ファイル"/><br>
      <h3>📁 パーソナルファイルマネージャ</h3>
      <b><i>「今日どのファイルを変えた？」</i></b><br><br>
      <div align="left">
        • ファイル変更の追跡<br>
        • 開いたドキュメント<br>
        • 編集のレビュー
      </div>
    </td>
    <td align="center" width="25%" valign="top">
      <img src="../usecase_digital_life.png" height="150" alt="デジタルライフ"/><br>
      <h3>🧩 デジタルライフの俯瞰</h3>
      <b><i>「午後はどう過ごした？」</i></b><br><br>
      <div align="left">
        • アプリ利用の追跡<br>
        • ワークフローの再生<br>
        • アクティビティの想起
      </div>
    </td>
  </tr>
</table>

## ✨ 主な機能

### 📹 常時オンのイベント取得
- **イベント駆動の記録**：タイマーも遅延もなく、マウス操作を十字マーカー付きで即座に取得。
- **豊富な文脈**：マウス操作を中心に、ウィンドウ、キーボード、クリップボード、通知、ファイルを追跡する 5 系統のレコーダー。

### 🌲 インテリジェントな記憶の階層
- **自動整理**：生ストリームを 5 段階（日 → セッション → アプリ → 場所 → アクション）に構造化。
- **スマート要約**：各レベルで LLM が要約し、ログを検索可能な知識ツリーへ変換。

### 🔍 ツリーベースの検索
- **ベクトル不要**：埋め込みと VDB をスキップ — ナビゲーションはツリー推論で行います。
- **トップダウン検索**：LLM が要約を読み、関連ブランチを選び、証拠まで掘り下げます。

### 🤖 ゼロ設定のエージェント連携
- **1 ファイル設定**：Skill ファイルを任意の AI エージェントに置くだけで統合。
- **すぐ使える**：CLI による画面履歴の問い合わせ、追加設定は不要。

### 🪶 超軽量・プライバシー優先
- **最小フットプリント**：SQLite + FTS5 で実行時 RAM 約 0.2GB。
- **ローカル＆オフライン**：データはマシン内に留まり、Ollama / vLLM / LM Studio で完全オフラインも可能。

### 🖥️ リッチな Web UI
- **視覚的探索**：インタラクティブなタイムライン、記憶ツリーのナビ、リアルタイム監視。
- **自然な対話**：自然言語でデジタル足跡全体とチャット。

<p align="center">
  <img src="../web.png" width="100%" alt="CatchMe Web ダッシュボード"/>
</p>


## 💡 CatchMe のアーキテクチャ

CatchMe は、生のデジタル活動を 3 つの並行ステージで構造化・検索可能な記憶に変換します。

### 🔄 記録 → 整理 → 推論：混沌を検索可能な記憶へ

**キャプチャ**。6 つのバックグラウンドレコーダーがウィンドウフォーカス、キー入力、マウス移動、スクリーンショット、クリップボード、通知を静かに追跡します。

**インデックス**。生イベントは階層アクティビティツリー（日 → セッション → アプリ → 場所 → アクション）に自動整理され、各ノードに LLM 要約が付きます。ベクトル埋め込みなしで高速かつ意味のある想起が可能です。

**検索**。質問に対し LLM が記憶ツリーを上から辿り、関連ノードを選び、スクリーンショットやキー入力などの生データを確認して、正確な回答を合成します。

<p align="center">
  <img src="../catchme-pipe.png" width="680" alt="CatchMe パイプライン：キャプチャ → インデックス → 検索"/>
</p>

### 🌲 階層アクティビティツリー
アクティビティツリーは CatchMe の記憶の中核です。デジタル生活の多層的・構造化ビューを提供し、高レベルの要約から細部まで辿れます。

<p align="center">
  <img src="../fig1_activity_tree.png" width="800" alt="階層アクティビティツリー"/>
</p>

### 🔍 インテリジェントなツリー検索
従来のベクトル検索は使いません。LLM がアクティビティツリーを直接ナビゲートし、日をまたぐ複雑な推論と、生の活動履歴からの精密な証拠収集が可能です。

<p align="center">
  <img src="../fig2_retrieval.png" width="800" alt="ツリー検索の流れ"/>
</p>

**📖 詳しくは**：[ブログ](https://hkuds.github.io/CatchMe) で設計の深掘りと技術解説を公開しています。

## 🧠 LLM 設定

### **❗️ データプライバシーについて**
• **100% ローカル保存**：スクリーンショット、キー入力、アクティビティツリーなどの生データはすべて `~/data/` に保存され、端末外に出ません。

• **オフライン優先**：ローカル LLM（Ollama、vLLM、LM Studio）でクラウドに依存しない完全オフライン運用が可能です。

• **⚠️ クラウド利用時の注意**：クラウド API を使う場合、日々の活動の要約に利用されます。**信頼できないエンドポイントはプライベートデータを晒す可能性があります** — プロバイダのデータ方針をよく確認してください。

### **📋 要件**
• **マルチモーダル**：テキスト + 画像を扱えるモデルであること。

• **コンテキスト長**：`config.json` の `max_tokens` 上限を超えるコンテキストウィンドウを確保してください。

• **コスト管理**：*強制的なコスト制限* には `llm.max_calls` で上限を設定するか、`filter.mouse_cluster_gap` を大きくして要約頻度を下げてください。

CatchMe はバックグラウンド要約とインテリジェント検索に LLM が必要です。**catchme init**（<a href="#-%E3%81%AF%E3%81%98%E3%82%81%E3%82%8B">はじめる</a>）で**ガイド付きセットアップ**するか、下記の**手動設定**に従ってください。

クラウド API の例：

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

ローカル / オフラインの例：

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
<summary><b>対応 LLM プロバイダ</b></summary>

| プロバイダ                 | 設定名                    | デフォルト API URL                                       | キー取得                                                              |
| ------------------------- | ------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------- |
| **OpenRouter** (gateway)  | `openrouter`             | `https://openrouter.ai/api/v1`                          | [openrouter.ai/keys](https://openrouter.ai/keys)                     |
| **Requesty** (gateway)    | `requesty`               | `https://router.requesty.ai/v1`                         | [app.requesty.ai/api-keys](https://app.requesty.ai/api-keys)         |
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

> OpenAI 互換の任意エンドポイントが使えます — `api_url` と `api_key` を直接指定してください。

</details>

<details>
<summary><b>全設定パラメータ</b></summary>

| セクション    | パラメータ                  | 既定値      | 説明                                                |
| ------------- | -------------------------- | ----------- | --------------------------------------------------- |
| **web**       | `host`                     | `127.0.0.1` | ダッシュボードのバインドアドレス                      |
|               | `port`                     | `8765`      | ダッシュボードのポート                              |
| **llm**       | `provider`                 | —           | LLM プロバイダ名（上表参照）                        |
|               | `api_key`                  | —           | プロバイダの API キー                               |
|               | `api_url`                  | *(自動)*    | カスタムエンドポイント；省略時はプロバイダごとに自動設定 |
|               | `model`                    | —           | モデル名（プロバイダ依存）                          |
|               | `max_calls`                | `0`         | サイクルあたりの最大 LLM 呼び出し回数（`0` = 無制限；コスト制限に設定） |
|               | `max_images_per_cluster`   | `5`         | イベントクラスタあたり送る最大スクリーンショット枚数   |
| **filter**    | `window_min_dwell`         | `3.0`       | 記録前に必要な最小ウィンドウ滞在時間（秒）            |
|               | `keyboard_cluster_gap`     | `3.0`       | キーボードイベントのクラスタ間隔（秒）               |
|               | `mouse_cluster_gap`        | `3.0`       | マウスイベントをまとめる時間間隔（秒）；**大きいほど LLM 要約が減る** |
| **summarize** | `language`                 | `en`        | 要約の出力言語（`en`、`zh` など）                    |
|               | `max_tokens_l0`–`l3`       | `1200`      | ツリー各レベルの最大トークン（L0=アクション … L3=セッション） |
|               | `temperature`              | `0.4`       | 要約用の温度                                        |
|               | `max_workers`              | `2`         | 並列要約ワーカー数                                  |
|               | `debounce_sec`             | `3.0`       | 要約トリガー前のデバウンス（秒）                     |
|               | `save_interval_sec`        | `5.0`       | ツリーの自動保存間隔（秒）                          |
| **retrieve**  | `max_prompt_chars`         | `42000`     | 検索プロンプトの最大文字数                          |
|               | `max_iterations`           | `15`        | ツリー走査の最大反復回数                            |
|               | `max_file_chars`           | `8000`      | 抽出ファイルからの最大文字数                        |
|               | `max_select_nodes`         | `7`         | 反復あたりの最大ノード選択数                        |
|               | `max_tokens_step`          | `4096`      | 検索ステップあたりの最大トークン数                  |
|               | `max_tokens_answer`        | `8192`      | 最終回答の最大トークン数                            |
|               | `temperature_select`       | `0.3`       | ノード選択の温度                                    |
|               | `temperature_answer`       | `0.5`       | 回答生成の温度                                      |
|               | `temperature_time_resolve` | `0.1`       | 時刻解決の温度                                      |
|               | `max_tokens_time_resolve`  | `1000`      | 時刻解決の最大トークン数                            |

</details>

## 🚀 はじめる

### 📦 インストール

```bash
git clone https://github.com/HKUDS/catchme.git && cd catchme

conda create -n catchme python=3.11 -y && conda activate catchme

pip install -e .
```

> **macOS** — システム設定 → プライバシーとセキュリティで *アクセシビリティ*、*入力監視*、*画面収録* を許可  
> **Windows** — グローバル入力監視のため管理者として実行

### ⚡ 初期化

```bash
catchme init                  # 対話式：プロバイダ、API キー、モデル
```

### 🔥 実行

```bash
catchme awake                 # 記録を開始
catchme web                   # 可視化とチャット

# または CLI から
catchme ask -- "今日は何をしていた？"
```

<details>
<summary><b>CLI リファレンス（抜粋）</b></summary>

| コマンド                    | 説明                                                    |
| --------------------------- | ------------------------------------------------------ |
| `catchme awake`             | 記録デーモンを起動                                     |
| `catchme web [-p PORT]`     | Web ダッシュボード（既定 `http://127.0.0.1:8765`）     |
| `catchme ask -- "質問"`     | 自然言語で活動を問い合わせ                             |
| `catchme cost`              | LLM トークン使用量（直近 10 分 / 今日 / 累計）        |
| `catchme disk`              | ストレージ内訳とイベント数                             |
| `catchme ram`               | 実行中プロセスのメモリ使用量                           |
| `catchme init`              | 対話式：プロバイダ、API キー、モデル                   |

</details>


## 🦞 CatchMe がエージェントを本当にパーソナルに
CatchMe は CLI エージェント（OpenClaw、NanoBot、Claude、Cursor など）向けの Skill として提供されます。

**🪶 エージェント連携：**  
CatchMe は自分で起動。エージェントは CLI コマンドだけで記憶を問い合わせます。

```bash
# 1. CatchMe を自分で起動
catchme awake

# 2. 軽量 Skill をエージェントに渡す
cp CATCHME-light.md ~/.cursor/skills/catchme/SKILL.md
```

**オプション B — フル Skill**（エージェントが CatchMe のライフサイクル全体を自律管理）：

```bash
cp CATCHME-full.md ~/.cursor/skills/catchme/SKILL.md
```

### 🔧 既存ワークフローへの組み込み

```python
from catchme import CatchMe
from catchme.pipelines.retrieve import retrieve

# 1. ワンライン検索 — 記録された活動全体の高速キーワード検索
with CatchMe() as mem:
    for e in mem.search("meeting notes"):
        print(e.timestamp, e.data)

# 2. LLM 検索 — 画面履歴への自然言語 Q&A
for step in retrieve("What was I working on this morning?"):
    if step["type"] == "answer":
        print(step["content"])
```

## 📊 コストと効率

*ベンチマーク：**MacBook Air M4 で 2 時間の連続・高負荷利用***


| 指標                                          | 値                                                                           |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| **実行時 RAM**                                | 約 0.2 GB                                                                    |
| **ディスク使用量**                            | 約 200 MB                                                                    |
| **トークン処理量**                            | 入力約 6 M、出力約 0.7 M                                                 |
| **LLM コスト** — `qwen-3.5-plus`              | 約 $0.42（[Aliyun DashScope](https://home.console.aliyun.com/home/dashboard/)） |
| **LLM コスト** — `gemini-3-flash-preview`     | 約 $5.00（[OpenRouter](https://openrouter.ai/models)）                       |
| **検索の完了までの時間**（質問依存）          | `gemini-3-flash-preview` 使用時、1 クエリあたり 5〜20 秒程度                  |


## 🚀 ロードマップ
コミュニティの声とともに CatchMe は進化します。予定している機能：

**マルチデバイス記録**。LAN 同期ですべてのマシン上の GUI 活動を取得・統合。

**動的クラスタリング**。実際の作業パターンとフローにより適合する適応的アルゴリズムで、不要なコストを抑える。

**データ活用の強化**。現在の処理パイプラインを超えて、スクリーンショットとメタデータからより深い洞察を得る。

> 🌟 **スターを付けて** 今後のアップデートをフォロー — 応援が開発の原動力になります。

コメント、バグ報告、アイデア、Pull Request、どんな貢献も歓迎です。[CONTRIBUTING.md](../../CONTRIBUTING.md) を参照してください。

## 🤝 コミュニティ

### 謝辞！

CatchMe は次の優れたオープンソースに触発されています：

| プロジェクト                                                     | インスピレーション                                           |
| --------------------------------------------------------------- | ----------------------------------------------------- |
| [ActivityWatch](https://github.com/ActivityWatch/activitywatch) | オープンソース活動追跡の先駆け                         |
| [Screenpipe](https://github.com/mediar-ai/screenpipe)           | AI エージェント向け画面録画基盤                         |
| [Windrecorder](https://github.com/Antonoko/Windrecorder)        | Windows 上の個人画面録画と検索                         |
| [OpenRecall](https://github.com/openrecall/openrecall)          | Windows Recall の OSS 代替                            |
| [Selfspy](https://github.com/selfspy/selfspy)                   | 古典的なデーモン型活動ログ                             |
| [PageIndex](https://github.com/HKUDS/PageIndex)                 | 埋め込みなしのツリー構造ドキュメント検索               |
| [MineContext](https://github.com/volcengine/MineContext)        | 先回り型コンテキスト認識 AI パートナーと画面キャプチャ |


### 🏛️ エコシステム

CatchMe は **[HKUDS](https://github.com/HKUDS)** エージェントエコシステムの一員です — パーソナル AI エージェントの基盤を構築します：

<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>超軽量パーソナル AI アシスタント</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>すべてのソフトウェアをエージェントネイティブに</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawWork"><b>ClawWork</b></a><br>
      <sub>AI アシスタントから AI コワーカーへ</sub>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>チーム自動化のためのエージェント群知能</sub>
    </td>
  </tr>
</table>
<br>
<p align="center">
  ✨ <b>CatchMe</b> をご覧いただきありがとうございます
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.catchme" alt="visitors"/>
</p>
