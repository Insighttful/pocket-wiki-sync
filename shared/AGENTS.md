# Shared

Weak models, clients, and cross-cutting concerns.

## Structure

```text
shared/
├── environment.py    # pydantic-settings based config (HeyPocketEnvironment, WikiEnvironment, SyncEnvironment)
├── pocket/           # HeyPocket API client and models (orthogonal module)
│   ├── __init__.py   # Public exports
│   ├── models.py     # Pydantic models (HeyPocketRecording, TranscriptData, etc.)
│   ├── config.py     # Configuration (HeyPocketConfig)
│   └── client.py     # API client (HeyPocketClient)
├── errors.py         # Custom exceptions (HeyPocketError, APIError, etc.)
├── sync_state.py     # Sync state management (.last-sync file handling)
└── __init__.py
```

## Key Knowledge for Agents

### Environment (shared/environment.py)

- Uses pydantic-settings with `.env` file as the source of truth:
  - `.env` values override any in-memory environment variables.
  - No in-memory env pollution across runs/commands.
- Core classes:
  - `Environment`: base class with env_file and env_file_priority config.
  - `WikiEnvironment`: WIKI_RAW_PATH configuration.
  - `HeyPocketEnvironment`: API key, base URL, concurrency settings.
  - `SyncEnvironment`: sync behavior (e.g., ignore_private_tags).
- Load via:
  - `get_wiki_env()` — prompts once for WIKI_RAW_PATH on first run if not set in .env.
  - `get_heypocket_env()` — HeyPocket API config.
  - `get_sync_env()` — sync behavior configuration.

### Pocket Module (shared/pocket/)

- **models.py**: Pydantic models for API data
  - `HeyPocketRecording` - main recording model with properties: plain_transcript, markdown_summary, mind_map, action_items
  - `TranscriptData`, `TranscriptMetadata`, `TranscriptSegment` - transcript structure
  - `SummarizationData`, `SummarizationV2` - AI summary data
  - `MindMapData`, `MindMapNode` - mind map structure
  - `ActionItem`, `ActionItemsData` - action items

- **config.py**: `HeyPocketConfig` - configuration loaded from environment

- **client.py**: `HeyPocketClient` - async API client with:
  - `list_recordings(start_date, page, limit)` - paginated list
  - `get_recording(id, include_transcript)` - full details
  - `download_transcripts(recordings)` - concurrent downloads with semaphore
  - `fetch_all_since(since_date)` - fetch all since last sync
- Uses tenacity for retry with exponential backoff
- Custom errors from `shared/errors.py`

### Sync State (shared/sync_state.py)

- Manages `.last-sync` file at project root (single source of truth; no wiki backup).
- Provides:
  - `get_last_sync()` — precise ISO timestamp.
  - `get_last_sync_date()` — YYYY-MM-DD for API calls.
  - `set_last_sync(timestamp)` — update last sync time.
- Used by CLI to avoid re-fetching already-synced recordings.

### Errors (shared/errors.py)

- `HeyPocketError` - base exception
- `APIError` - API request failed
- `AuthenticationError` - invalid API key
- `RateLimitError` - rate limit exceeded
- `NotFoundError` - resource not found
