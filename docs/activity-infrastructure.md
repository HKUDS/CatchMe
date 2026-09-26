# Local activity infrastructure (dev)

The **应用乐园 (App Garden)** homepage presents familiar apps as cards with independent monitoring switches. Each app opens a view designed for its data: continuous coding-agent conversations, Office documents, WeChat files, browser history/bookmarks/downloads, editor workspaces, or creative projects. The top-level **支持的应用** directory lists all 13 supported apps, their capabilities, availability, and full-mode support; other discovered apps are listed separately. **高级数据设置 (Advanced data settings)** retains installed-app discovery, source controls, raw observations, local statistics, and optional analysis through a user-configured LLM. This is a first macOS implementation; installed-app discovery and foreground sampling are not yet portable to Windows/Linux.

## Run

```sh
catchme sources scan
catchme sources list
catchme sources enable system.foreground
catchme sources collect
catchme web
# Optional continuous collection without screen / input recorders:
catchme sources watch --interval 10
```

Open `http://127.0.0.1:8765`. The app gallery scans on first use when no apps are available; **刷新应用** rescans explicitly. Enable the apps you want to monitor. `catchme web` starts a local background collector, which refreshes enabled sources every 15 seconds and samples selected app context about once a second, even after the browser closes; **更新记录** refreshes a detail timeline without interrupting expanded records during background collection. In advanced data settings, **Collect now** runs a pass and the live checkbox collects every ten seconds while that page is open. `catchme sources watch` collects independently of the dashboard; `catchme awake` also collects enabled sources alongside existing recorders. A process lock prevents overlapping collection passes. New sources default off unless their app already has an explicit enabled preference; scanning preserves existing individual source switches; disabling preserves previously collected records.

## App monitoring

The curated gallery includes Excel, PowerPoint, Word, WeChat, Claude, Codex, ChatGPT, Cursor, VS Code, CapCut, Notion, Safari, and Chrome. A switch controls the app’s mapped sources and whether its foreground observations are saved. Pausing preserves historical activity and does not pause other apps. Existing source preferences initialize app switches until an explicit app preference is saved; rescanning preserves choices. Foreground collection saves only enabled curated apps. Independently enabled advanced sources remain available; legacy screen/input recorders are separate controls.

App timelines combine dedicated source records with foreground samples, ordered by source timestamp and ID, with cursor pagination. Foreground samples indicate observed use, not duration. WeChat provides attachment metadata and observed document-open references. ChatGPT provides usage records in basic mode; full mode can observe readable foreground UI text. Claude conversation records come from local Claude Code sessions. Office records contain recent document references, not cell edits or document contents. The interface explains each app’s coverage.

Application icons in `catchme/static/img/apps/` are thumbnails extracted from installed macOS application bundles for identification. Names and icons belong to their respective owners and do not imply affiliation.

## Current readers

| Source | Collected evidence | Limitations |
| --- | --- | --- |
| Installed apps | Bundle ID, display name, version, category, path | Inventory is not activity; application folders plus two grouping levels |
| Foreground apps | App, bundle ID, PID, observed time, idle state | Point samples, not measured durations; ten-second deduplication, idle threshold 300 seconds |
| Claude Code / Codex | User and assistant text, session/project/model context, source file/offset; full mode adds recorded tool calls/results | Hidden reasoning and image blobs excluded; bounded incremental backfill with explicit gaps for oversized records |
| Safari / Chrome profiles | Visit time, URL, title, profile; bookmarks/folders and download indexes | Safari may need Full Disk Access; profile errors are isolated; download indexes do not guarantee files still exist |
| Local app logs | File path, byte size, modification time | Metadata only, no semantic log parser; not evidence of user interaction |
| Existing CatchMe events | Existing raw event payloads, original event ID | Available after a dashboard scan finds `data.db`; existing recorder APIs remain intact |
| Excel / Word / PowerPoint | Recent document paths and last-used timestamps from Office secure-bookmark indexes | Bookmark capability bytes and document contents are excluded; no cell/edit history |
| Cursor / VS Code | Recent files and workspace references | Snapshot observations; source does not provide exact open times |
| Cursor conversation index | Conversation titles, workspace scope, update time | No transcript bodies; separate from Claude/Codex readers |
| CapCut / Jianying | Project names, paths, creation/modification time and native duration metadata | Project index only; native duration is not editing time |
| Pages / Numbers / Keynote and other creative apps | Standard macOS per-app recent-document lists (.sfl3/.sfl2) | May need Full Disk Access; unavailable/missing lists are reported; no document contents |
| WeChat | Attachment names, paths, sizes and modification times; opened documents identified by foreground AXDocument paths inside WeChat attachment roots | File presence does not prove opening or message direction; exported copies outside these roots cannot be attributed reliably; no message-database decryption |
| Safari bookmarks / downloads | Bookmark URLs, titles and folders; download URLs and paths | Full Disk Access may be required; bookmark timestamps reflect index modification, and download entries do not prove completion |

Apps are classified into communication, development, creative, office, browser, and other using explicit name/bundle-ID rules. App-owned document/project readers live in `catchme/sources/documents.py`; new readers are registered in `catchme/sources/collect.py` and source discovery in `catalog.py`; the dashboard presents capabilities and failures without pretending every installed app has a working business-data reader.

## Full monitoring and evidence

Ten apps currently offer an explicit **完整监控** mode: Excel, PowerPoint, Word, WeChat, Claude, Codex, ChatGPT, Cursor, VS Code, and Notion. Switching requires an unchecked scope acknowledgement in the app detail dialog. The API requires `consent: true`; saving a mode alone does not enable a paused app. The UI's **开启完整监控** action also enables that app. Returning to basic mode or pausing preserves history.

On macOS, full monitoring reads the foreground app’s accessible window text and observes changes in its focused text field. It records window changes, clicks, throttled scrolls, shortcuts, and special keys through a listen-only event tap. Printable key events are not logged; text comes from accessible fields. Secure/protected fields are excluded. Capture is bounded to 400 accessibility nodes, about 0.65 seconds per tree, and 16,000 text characters. Fast input changes, unexposed controls, background conversations, and content outside the sampled tree can be missed. UI text is labelled as observed content, never inferred to be an incoming/outgoing message; Enter is not proof that a message was sent. There is no screenshot, microphone, clipboard-wide, or cloud capture in this collector.

The native collector requires existing Accessibility permission and may need Input Monitoring permission for actions. It does not request or grant OS permissions automatically. Per-app enablement and consent are rechecked in a write transaction; stale observations after pause, downgrade, or a new consent generation are discarded. The event callback does no AX queries or database work and retains actions only for the selected foreground PID. A process lock prevents duplicate live collectors. Stopping the web service stops this collector; existing legacy `awake` recorders have independent controls.

Claude Code and Codex use their local JSONL sessions as the primary source, including sessions that are not currently open. Basic mode imports user/assistant text with session ID, project directory, model when available, and file/offset provenance. Full mode also backfills recorded tool calls, arguments and results, without executing them. Returning to basic mode stops new tool collection. Existing conversation IDs remain stable through enrichment and mode changes. The detail page opens with searchable session cards, paginated in groups of 30. Search matches any captured content while retaining the whole session. Selecting a session opens chronological user/assistant messages, expandable context, and paired tool calls/results; pagination continues the same chat. Long messages can be expanded without losing text. Office documents and project indexes deduplicate repeated snapshots; browser bookmarks retain folder and profile identity. Native session records retain explicit roles; UI snapshots retain uncertainty. No new collected content is automatically sent to an LLM.

## Storage and incremental behavior

`~/.catchme/activity.db` uses SQLite WAL and schema version 4 (automatically migrated from versions 1–3). `app_preferences` stores app-level enablement, mode and consent generation; `source_locations` stores explicit additional paths per source; `applications` stores inventory; `sources` stores enablement, availability, errors, and checkpoints; `activity` stores normalized observations plus source payloads; `analyses` stores model, service, exact aggregate input, and output. The existing `data.db` is preserved.

Each source checkpoint commits in the same transaction as its observations. `(source, external_id)` deduplicates replay. JSONL readers retain incomplete trailing records, resume by byte offset, and detect inode changes/truncation. They target 2 MiB per file and approximately 16 MiB per pass (one complete line may exceed the target), with an 8 MiB maximum line. Oversized lines are streamed past with a visible `capture_gap` observation, allowing other records to continue. Incomplete trailing records wait for the writer. Conversation text is retained in full within the JSONL line limit; tool text currently retains up to 16,000 characters. Image blobs and hidden reasoning are excluded. Transcript responses target 2 MiB and 80 records, but always include at least one complete message. A covering session index keeps browsing independent of repeated full-body scans. Failed JSONL files or browser profiles do not discard successful records/checkpoints from other locations; the source reports partial availability. Metadata scans inspect up to 5,000 entries per source per pass. Browser readers read 1,000 visits per pass using a short read-only SQLite connection that includes committed WAL data. Full scans run only on explicit request.

Normalized fields: `id`, `source`, `external_id`, `ts` (source event time, or file modification time if unavailable), `observed` (ingest time), `app`, `category`, `kind`, `title`, `payload`. Raw observations are normalized, text-limited, and masked; they are not byte-for-byte archival copies. Basic masking targets common token/password patterns; it does not guarantee removal of private data. Sources remain local until a caller explicitly uses them; the dashboard analysis endpoint transmits only aggregate counts and app labels, never raw transcript text. Existing CatchMe chat/summarization features retain their existing data flow.

Statistics use the full selected time range and source/category filters, independent of event pagination. The raw feed orders by ingestion ID, paginates with `before`, and filters app/title search independently of aggregate statistics. Counts and foreground samples do not measure productivity or precise active duration. Historical imports can have old event times and recent observation times. Analyses retain the source/category filters and time interval in their input provenance.

## Service + model configuration

Following DeepSeek Harness's separation of connection routes and model selection, named `services` own provider, endpoint, protocol, credential reference, and allowed model IDs. `llm.service` and `llm.model` select the active pair. Every existing `LLM()` consumer resolves through this selection; legacy flat `llm` configurations still work when `llm.service` is absent. Native Anthropic/Gemini protocols are not implemented: use an OpenAI-compatible endpoint or gateway.

```json
{
  "services": {
    "my-deepseek": {
      "provider": "deepseek",
      "api_url": "https://api.deepseek.com/v1",
      "api_key_env": "DEEPSEEK_API_KEY",
      "wire_api": "completions",
      "models": ["deepseek-chat", "deepseek-reasoner"]
    }
  },
  "llm": {"service": "my-deepseek", "model": "deepseek-chat"}
}
```

An inline `api_key` is also supported. An explicit `api_key_env` takes precedence. Environment variables must be present in the process running CatchMe. Dashboard settings preserve a saved key when the key field is blank; remove a saved key by editing local `config.json`. The API never returns service keys or custom header values. Model selection validates the configured model list; unknown services/models fail rather than silently routing elsewhere. Existing long-lived LLM instances pick up a changed selection when recreated (restart `awake` to switch an already running summarizer).

## Web provider and model management

Open **模型设置 (Models)** in the sidebar. Create a named service, choose a provider preset or a custom OpenAI-compatible endpoint, and enter a key or credential environment variable. **Test provider** verifies the model-catalog endpoint and reports authentication/connection errors and latency. **Fetch model list** loads `/models`; search and select IDs, then add them to the configured list. Model IDs can also be entered manually when a provider has no catalog. **Save provider** persists the connection and model list without changing the active pair; a new service can be saved before any models are configured.

**Test model** sends the fixed text `Reply with OK.` using the draft endpoint, selected protocol and chosen model. It makes a real generation request (up to 64 output tokens), can incur a small provider charge, and returns response text and latency. Reasoning models may exhaust this small budget before producing visible text; that outcome is reported distinctly. Tests work before saving and transmit no collected activity. Provider diagnostics use a 20-second timeout, no retries and no redirects. **Save & use this model** adds the ID to the service catalog and selects the pair for subsequent LLM instances. Editing an active service cannot remove its currently selected model unless another valid model is selected at the same time.

Saved secrets are not returned to the client. Blank keys preserve an existing key on the same endpoint. Changing a saved endpoint requires an explicitly supplied key or environment reference; previous credentials and authorization headers are not silently forwarded to a new host. The existing flat provider configuration remains active until a named pair is selected.

## HTTP API

Read: `/api/activity/sources`, `/api/activity/events`, `/api/activity/facts`, `/api/activity/analyses`, `/api/activity/models`. Mutation (JSON POST): `/api/activity/scan`, `/api/activity/collect`, `/api/activity/sources/<id>` (`enabled` boolean), `/api/activity/analyze`, `/api/activity/models`, `/api/activity/models/select`. Events/facts accept Unix-second `since`/`until`, `source` and `category`; events also accept `q`, `limit`, `before`. New mutation routes reject cross-origin browser requests. The app is a local tool without authentication: keep the default loopback bind.

Provider diagnostics: GET `/api/activity/providers/presets`; JSON POST `/api/activity/providers/test` and `/api/activity/providers/models` take `{name, service}` (a saved name with draft overrides); POST `/api/activity/models/test` also takes `model`. Results contain `ok`, latency or a sanitized error/status. Saving `/api/activity/models` without `model` leaves the active selection unchanged.

App gallery: GET `/api/library/apps`; POST `/api/library/apps/<id>/monitor` with `{ "enabled": true }`; GET `/api/library/apps/<id>/activity` with an optional `before` cursor from the previous response.

Monitoring: POST `/api/library/apps/<id>/mode` with `{ "mode": "full", "consent": true }` or `{ "mode": "basic" }`. Gallery responses include local collector health and permission status. GET `/api/library/apps/<id>/sessions` returns `{sessions, total, next}` and accepts `q` / `before`. GET `/api/library/apps/<id>/transcript` takes `session` / `after` and returns chronological messages with a continuation cursor; activity queries also accept `kind` (`all`, `files`, `content`, `actions`, `browsing`), `q`, and `session`.

## Data locations and app-specific views

Open **数据位置与采集状态** at the bottom of an app page to inspect default locations and add alternate paths. Claude/Codex accept session directories or individual JSONL files; WeChat accepts attachment directories. Browser, Office, editor, and creative readers accept the complete path to their native index file. Saving checks availability and rescans without enabling collection or changing existing app/source switches. It neither moves nor writes to application data.

Discovery honors `CLAUDE_CONFIG_DIR`, `CODEX_HOME` (including `archived_sessions`), and `CHROME_USER_DATA_DIR`. Chrome discovery checks Default, Profile directories, and Local State profile entries. Editor discovery includes named profiles and VS Code Insiders. Chrome/editor path discovery understands macOS, Windows AppData, and Linux XDG layouts; installed-app discovery and live monitoring are still macOS implementations, and the collector currently uses Unix process locks. Office checks container and legacy preference locations. WeChat attachment discovery includes alternate layouts across app versions; additional paths cover portable or relocated installations.

GET `/api/library/catalog` returns the supported directory and other discovered apps. GET `/api/library/apps/<id>/content` takes a view `tab`, `q`, and `before`, returning an appropriate layout and deduplicated collection. GET/POST `/api/library/apps/<id>/locations` reads/saves `{locations: {source_id: [absolute_paths]}}`; paths are app-scoped, at most 20 per source. These features run locally without an LLM request.
