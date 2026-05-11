"""Tests for shared/pocket/models.py."""

import pytest

from shared.pocket.models import (
    ActionItem,
    HeyPocketRecording,
    SummarizationData,
    SummarizationSummary,
    SummarizationV2,
    TranscriptData,
    TranscriptMetadata,
    TranscriptSegment,
)


class TestHeyPocketRecording:
    """Tests for HeyPocketRecording model."""

    def test_minimal_recording(self):
        """Test creating a minimal recording."""
        rec = HeyPocketRecording(id="test-123", title="Test Recording")
        assert rec.id == "test-123"
        assert rec.title == "Test Recording"
        assert rec.slug == "test-recording"

    def test_slug_generation(self):
        """Test slug is filesystem-safe."""
        rec = HeyPocketRecording(id="abc", title="Hello World! Test 123")
        assert rec.slug == "hello-world-test-123"

    def test_tags_normalized_from_dicts(self):
        """Test tags are normalized from dict format."""
        # Note: tags normalization happens in wiki.py _normalize_tags, not in model
        # The model stores raw tags, wiki.py converts them
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            tags=[
                {"id": "tag-1", "name": "ai", "color": None},
                {"id": "tag-2", "name": "work", "color": "#ff0000"},
            ],
        )
        # Model stores as-is, normalization happens in output
        assert len(rec.tags) == 2
        assert rec.tags[0]["name"] == "ai"

    def test_tags_normalized_from_strings(self):
        """Test tags work with string list."""
        rec = HeyPocketRecording(id="abc", title="Test", tags=["ai", "work"])
        assert rec.tags == ["ai", "work"]

    def test_plain_transcript_from_raw(self):
        """Test plain_transcript prefers raw_transcript."""
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            raw_transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100.0),
                segments=[],
                text="Raw transcript text",
            ),
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100.0),
                segments=[],
                text="Regular transcript text",
            ),
        )
        assert rec.plain_transcript == "Raw transcript text"

    def test_plain_transcript_fallback_to_transcript(self):
        """Test plain_transcript falls back to transcript.text."""
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100.0),
                segments=[],
                text="Regular transcript text",
            ),
        )
        assert rec.plain_transcript == "Regular transcript text"

    def test_plain_transcript_from_segments(self):
        """Test plain_transcript falls back to concatenated segments."""
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100.0),
                segments=[
                    TranscriptSegment(start=0.0, end=5.0, text="Hello"),
                    TranscriptSegment(start=5.0, end=10.0, text="World"),
                ],
            ),
        )
        assert rec.plain_transcript == "Hello\nWorld"

    def test_markdown_summary_from_summarization(self):
        """Test markdown_summary extracts from v2 summary."""
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            summarizations={
                "sum-1": SummarizationData(
                    id="sum-1",
                    v2=SummarizationV2(
                        summary=SummarizationSummary(markdown="# Summary\nTest content")
                    ),
                )
            },
        )
        assert rec.markdown_summary == "# Summary\nTest content"

    def test_mind_map_from_summarization(self):
        """Test mind_map extracts from v2 (via API-style dict)."""
        # Use API-style dict with camelCase keys (how the real API returns data)
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            summarizations={
                "sum-1": SummarizationData.model_validate(
                    {
                        "id": "sum-1",
                        "v2": {
                            "mindMap": {
                                "type": "flow",
                                "nodes": [
                                    {
                                        "node_id": "root",
                                        "parent_node_id": "",
                                        "title": "Root",
                                        "color": "#fff",
                                    }
                                ],
                            }
                        },
                    }
                ),
            },
        )
        assert rec.mind_map is not None
        assert rec.mind_map.type == "flow"
        assert len(rec.mind_map.nodes) == 1

    def test_action_items_from_summarization(self):
        """Test action_items extracts from v2 (via API-style dict)."""
        # Use API-style dict with camelCase keys (how the real API returns data)
        rec = HeyPocketRecording(
            id="abc",
            title="Test",
            summarizations={
                "sum-1": SummarizationData.model_validate(
                    {
                        "id": "sum-1",
                        "v2": {
                            "actionItems": {
                                "actions": [
                                    {
                                        "id": "action-1",
                                        "label": "Do something",
                                        "assignee": "me",
                                        "priority": "high",
                                    }
                                ]
                            }
                        },
                    }
                ),
            },
        )
        assert len(rec.action_items) == 1
        assert rec.action_items[0].label == "Do something"
        assert rec.action_items[0].assignee == "me"


class TestTranscriptData:
    """Tests for TranscriptData model."""

    def test_transcript_with_metadata(self):
        """Test transcript with metadata."""
        data = TranscriptData(
            metadata=TranscriptMetadata(duration=300.5, language="en", source="wizper"),
            segments=[],
            text="Full transcript",
        )
        assert data.metadata.duration == pytest.approx(300.5)
        assert data.metadata.source == "wizper"
        assert data.text == "Full transcript"


class TestActionItem:
    """Tests for ActionItem model."""

    def test_action_item_fields(self):
        """Test action item parsing from API-style dict with camelCase."""
        # This is how the API actually sends data - uses camelCase aliases
        item = ActionItem.model_validate(
            {
                "id": "action-1",
                "label": "Complete task",
                "assignee": "john",
                "context": "Important context",
                "dueDate": "2026-05-15",
                "priority": "high",
                "status": "TODO",
                "isCompleted": False,
                "globalActionItemId": "global-123",
                "type": "create_reminder",
            }
        )
        assert item.label == "Complete task"
        assert item.assignee == "john"
        assert item.priority == "high"
        assert item.global_action_item_id == "global-123"
        assert item.action_type == "create_reminder"
