"""Tests for wiki output module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from modules.wiki import WikiOutput
from shared.pocket.models import (
    ActionItem,
    ActionItemsData,
    HeyPocketRecording,
    MindMapData,
    MindMapNode,
    SummarizationData,
    SummarizationSummary,
    SummarizationV2,
    TranscriptData,
    TranscriptMetadata,
)


@pytest.fixture
def temp_wiki_path(tmp_path):
    """Create a temporary wiki directory.

    Returns:
        Path to the temporary wiki directory.
    """
    return tmp_path / "wiki"


@pytest.fixture
def mock_env(temp_wiki_path):
    """Create a mock WikiEnvironment.

    Returns:
        Mock WikiEnvironment instance.
    """
    env = MagicMock()
    env.wiki_raw_path = temp_wiki_path
    return env


@pytest.fixture
def wiki_output(mock_env):
    """Create WikiOutput instance.

    Returns:
        WikiOutput instance.
    """
    return WikiOutput(mock_env)


@pytest.fixture
def sample_recording():
    """Create a sample HeyPocketRecording for testing.

    Returns:
        HeyPocketRecording instance with sample data.
    """
    # Create mind map
    mind_map = MindMapData(
        type="tree",
        nodes=[
            MindMapNode(
                node_id="node-1",
                parent_node_id="",
                title="Main Topic",
                color="#FF0000",
            ),
            MindMapNode(
                node_id="node-2",
                parent_node_id="node-1",
                title="Sub Topic",
                color="#00FF00",
            ),
        ],
    )

    # Create action items
    action_items = ActionItemsData(
        actions=[
            ActionItem(
                id="action-1",
                label="Complete the task",
                assignee="John",
                context="Context info",
                due_date="2026-05-15",
                priority="high",
                status="TODO",
                is_completed=False,
                global_action_item_id=None,
                action_type="task",
            ),
        ],
    )

    # Create v2 summarization
    v2 = SummarizationV2(
        summary=SummarizationSummary(markdown="# Summary\n\nThis is the AI summary."),
    )
    # Set fields that require validation_alias for direct assignment
    v2.mind_map = mind_map
    v2.action_items = action_items

    # Create summarization data
    summarization = SummarizationData(
        id="sum-123",
        summarization_id="sum-123",
        processing_status="completed",
        v2=v2,
    )

    return HeyPocketRecording(
        id="rec-123",
        title="Test Meeting Notes",
        created_at=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
        updated_at=datetime(2026, 5, 10, 15, 0, tzinfo=UTC),
        recording_at=datetime(2026, 5, 10, 14, 0, tzinfo=UTC),
        duration=3600,
        state="completed",
        language="en",
        description="Test description",
        tags=["work", "meeting"],
        transcript=TranscriptData(
            metadata=TranscriptMetadata(
                duration=3600,
                language="en",
                language_probability=0.95,
                source="whisper",
            ),
            segments=[],
            text="This is the transcript text.",
        ),
        raw_transcript=None,
        summarizations={"v2": summarization},
    )


class TestNormalizeTags:
    """Tests for _normalize_tags method."""

    def test_normalize_string_tags(self, wiki_output):
        """Test normalizing list of string tags."""
        tags = ["work", "meeting", "important"]
        result = wiki_output._normalize_tags(tags)
        assert result == ["work", "meeting", "important"]

    def test_normalize_dict_tags(self, wiki_output):
        """Test normalizing list of dict tags."""
        tags = [
            {"name": "work", "id": "tag-1"},
            {"label": "meeting", "id": "tag-2"},
            {"id": "tag-3"},
        ]
        result = wiki_output._normalize_tags(tags)
        assert result == ["work", "meeting", "tag-3"]

    def test_normalize_mixed_tags(self, wiki_output):
        """Test normalizing mixed string and dict tags."""
        tags = ["work", {"name": "meeting"}, "important"]
        result = wiki_output._normalize_tags(tags)
        assert result == ["work", "meeting", "important"]

    def test_normalize_empty_list(self, wiki_output):
        """Test normalizing empty tag list."""
        result = wiki_output._normalize_tags([])
        assert result == []


class TestFormatRecording:
    """Tests for _format_recording method."""

    def test_frontmatter_generation(self, wiki_output, sample_recording):
        """Test YAML frontmatter is generated correctly."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert result.startswith("---")
        assert "id: rec-123" in result
        assert "title: Test Meeting Notes" in result
        assert "state: completed" in result
        assert "language: en" in result

    def test_frontmatter_tags(self, wiki_output, sample_recording):
        """Test tags are included in frontmatter."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert "tags:" in result
        assert "work" in result
        assert "meeting" in result

    def test_summary_section(self, wiki_output, sample_recording):
        """Test Summary section is included when available."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert "## Summary" in result
        assert "This is the AI summary." in result

    def test_mind_map_section(self, wiki_output, sample_recording):
        """Test Mind Map section is included when available."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert "## Mind Map" in result
        assert "Type: tree" in result
        assert "### Nodes" in result
        assert "Main Topic" in result

    def test_action_items_section(self, wiki_output, sample_recording):
        """Test Action Items section is included when available."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert "## Action Items" in result
        assert "Complete the task" in result
        assert "assignee: John" in result
        assert "due_date: 2026-05-15" in result

    def test_transcript_section(self, wiki_output, sample_recording):
        """Test Transcript section is included when available."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        assert "## Transcript" in result
        assert "This is the transcript text." in result

    def test_section_ordering(self, wiki_output, sample_recording):
        """Test sections appear in correct order."""
        result = wiki_output._format_recording(sample_recording, "test-file.md")

        # Find positions of sections
        summary_pos = result.find("## Summary")
        mind_map_pos = result.find("## Mind Map")
        action_items_pos = result.find("## Action Items")
        transcript_pos = result.find("## Transcript")

        assert summary_pos < mind_map_pos < action_items_pos < transcript_pos

    def test_no_summary_when_missing(self, wiki_output):
        """Test Summary section is not included when not available."""
        recording = HeyPocketRecording(
            id="rec-456",
            title="No Summary Recording",
            created_at=datetime(2026, 5, 10, tzinfo=UTC),
            state="completed",
            language="en",
            tags=[],
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100, language="en"),
                segments=[],
                text="Transcript text",
            ),
        )
        result = wiki_output._format_recording(recording, "test.md")

        assert "## Summary" not in result

    def test_completed_action_item_unchecked(self, wiki_output):
        """Test completed action items show [x]."""
        # Create action items
        action_items = ActionItemsData(
            actions=[
                ActionItem(
                    id="action-1",
                    label="Done task",
                    is_completed=True,
                ),
            ],
        )

        v2 = SummarizationV2(summary=SummarizationSummary(markdown=""))
        v2.action_items = action_items

        summarization = SummarizationData(
            id="sum-1",
            summarization_id="sum-1",
            processing_status="completed",
            v2=v2,
        )

        recording = HeyPocketRecording(
            id="rec-789",
            title="Completed Action",
            created_at=datetime(2026, 5, 10, tzinfo=UTC),
            state="completed",
            language="en",
            tags=[],
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100, language="en"),
                segments=[],
                text="Transcript",
            ),
            summarizations={"v2": summarization},
        )
        result = wiki_output._format_recording(recording, "test.md")

        assert "- [x] **Done task**" in result

    def test_incomplete_action_item_unchecked(self, wiki_output):
        """Test incomplete action items show [ ]."""
        # Create action items
        action_items = ActionItemsData(
            actions=[
                ActionItem(
                    id="action-2",
                    label="Pending task",
                    is_completed=False,
                ),
            ],
        )

        v2 = SummarizationV2(summary=SummarizationSummary(markdown=""))
        v2.action_items = action_items

        summarization = SummarizationData(
            id="sum-2",
            summarization_id="sum-2",
            processing_status="completed",
            v2=v2,
        )

        recording = HeyPocketRecording(
            id="rec-790",
            title="Incomplete Action",
            created_at=datetime(2026, 5, 10, tzinfo=UTC),
            state="completed",
            language="en",
            tags=[],
            transcript=TranscriptData(
                metadata=TranscriptMetadata(duration=100, language="en"),
                segments=[],
                text="Transcript",
            ),
            summarizations={"v2": summarization},
        )
        result = wiki_output._format_recording(recording, "test.md")

        assert "- [ ] **Pending task**" in result


class TestSaveRecording:
    """Tests for save_recording method."""

    def test_save_recording_creates_file(
        self, wiki_output, sample_recording, temp_wiki_path
    ):
        """Test save_recording creates the file."""
        result = wiki_output.save_recording(sample_recording)

        assert result is not None
        assert result.exists()
        assert result.name == "2026-05-10-test-meeting-notes.md"

    def test_save_recording_idempotent(
        self, wiki_output, sample_recording, temp_wiki_path
    ):
        """Test save_recording skips existing files."""
        # Save first time
        result1 = wiki_output.save_recording(sample_recording)
        assert result1 is not None

        # Save again - should return None (skipped)
        result2 = wiki_output.save_recording(sample_recording)
        assert result2 is None

    def test_save_recording_without_transcript(self, wiki_output):
        """Test save_recording returns None for recording without transcript."""
        recording = HeyPocketRecording(
            id="rec-no-transcript",
            title="No Transcript",
            created_at=datetime(2026, 5, 10, tzinfo=UTC),
            state="completed",
            language="en",
            tags=[],
            transcript=None,
        )
        result = wiki_output.save_recording(recording)

        assert result is None


class TestEnsureDirectories:
    """Tests for ensure_directories method."""

    def test_ensure_directories_creates_paths(self, wiki_output, temp_wiki_path):
        """Test ensure_directories creates all required directories."""
        wiki_output.ensure_directories()

        assert temp_wiki_path.exists()

    def test_ensure_directories_idempotent(self, wiki_output, temp_wiki_path):
        """Test ensure_directories is safe to call multiple times."""
        wiki_output.ensure_directories()
        wiki_output.ensure_directories()  # Should not raise

        assert temp_wiki_path.exists()
