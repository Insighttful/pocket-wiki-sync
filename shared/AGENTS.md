# Shared

Weak models, clients, and cross-cutting concerns.

## Structure

```text
shared/
├── environment.py    # pydantic-settings based config (HeyPocketEnvironment, WikiEnvironment)
├── pocket/           # HeyPocket API client and models (orthogonal module)
│   ├── __init__.py   # Public exports
│   ├── models.py     # Pydantic models (HeyPocketRecording, TranscriptData, etc.)
│   ├── config.py     # Configuration (HeyPocketConfig)
│   └── client.py     # API client (HeyPocketClient)
├── errors.py         # Custom exceptions (HeyPocketError, APIError, etc.)
└── __init__.py
```

## Child Modules

- [environment.py](environment/AGENTS.md) - if becomes package
- [pocket/](pocket/AGENTS.md) - orthogonal module with models, config, client

## Key Knowledge for Agents

### Environment (shared/environment.py)

- Uses pydantic-settings with `.env` file
- `HeyPocketEnvironment` - API key, base URL, concurrency settings
- `WikiEnvironment` - wiki path configuration
- Load via: `get_heypocket_env()`, `get_wiki_env()`

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

### Errors (shared/errors.py)

- `HeyPocketError` - base exception
- `APIError` - API request failed
- `AuthenticationError` - invalid API key
- `RateLimitError` - rate limit exceeded
- `NotFoundError` - resource not found
