# Pocket Module

Orthogonal module for HeyPocket AI API client and models.

## Structure

```text
shared/pocket/
├── __init__.py   # Public exports (HeyPocketClient, HeyPocketConfig, HeyPocketRecording)
├── models.py     # Pydantic models
├── config.py     # Configuration
└── client.py     # API client
```

## Models Schema (models.py)

### HeyPocketRecording

Main model for a recording. Properties:

- `id` (`str`) - unique identifier
- `title` (`str`) - recording title
- `created_at` (`datetime`) - when created in system
- `updated_at` (`datetime | None`) - last update time
- `recording_at` (`datetime | None`) - when recording actually happened
- `duration` (`int | None`) - duration in seconds
- `state` (`str`) - recording state (e.g., "completed")
- `language` (`str`) - language code (e.g., "en")
- `description` (`str | None`) - description (usually null)
- `tags` (`list[str]`) - normalized list of tag names
- `transcript` (`TranscriptData | None`) - transcript with metadata and segments
- `raw_transcript` (`TranscriptData | None`) - raw transcript data
- `summarizations` (`dict[str, SummarizationData]`) - AI-generated summaries

**Computed properties:**

- `plain_transcript` (`str | None`) - plain text transcript
- `markdown_summary` (`str | None`) - AI-generated markdown summary
- `mind_map` (`MindMapData | None`) - structured mind map nodes
- `action_items` (`list[ActionItem]`) - extracted action items
- `slug` (`str`) - filesystem-safe slug from title

### TranscriptData

- `metadata` (`TranscriptMetadata`) - duration, language, source
- `segments` (`list[TranscriptSegment]`) - individual segments with start/end/text
- `text` (`str | None`) - full plain text

### SummarizationData

- `id` (`str`) - summarization ID
- `summarization_id` (`str`) - alias for ID
- `processing_status` (`str`) - status (e.g., "completed")
- `v2` (`SummarizationV2 | None`) - v2 summary data

### ActionItem

- `id` (`str`) - action item ID
- `label` (`str`) - action description
- `assignee` (`str | None`) - who it's assigned to
- `context` (`str | None`) - additional context
- `due_date` (`str | None`) - due date if set
- `priority` (`str`) - priority (default "medium")
- `status` (`str`) - status (default "TODO")
- `is_completed` (`bool`) - completion status
- `global_action_item_id` (`str | None`) - global ID
- `action_type` (`str | None`) - type of action

## Public API (via shared.pocket or shared)

### Config (config.py)

```python
from shared.pocket import HeyPocketConfig

config = HeyPocketConfig.from_environment()
```

### Client (client.py)

```python
from shared import HeyPocketClient

async with HeyPocketClient(config) as client:
    recordings, pagination = await client.list_recordings(start_date="2026-05-01")
    recording = await client.get_recording(rec_id, include_transcript=True)
    await client.download_transcripts(recordings)
    all_recordings = await client.fetch_all_since(since_date="2026-05-01")
```

## Design Principles

- **Minimal entry/exit surface**: All public API exposed via `__init__.py`
- **Orthogonal**: models, config, client are independent
- **Pydantic validation**: All API responses validated at boundary
