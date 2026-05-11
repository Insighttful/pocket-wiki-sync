"""Pydantic models for HeyPocket API data.

Strong models for transcript, summarization, mind map, and action items.
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TranscriptMetadata(BaseModel):
    """Metadata about the transcript."""

    duration: float | None = None
    language: str = "en"
    language_probability: float = 1.0
    source: str = "unknown"


class TranscriptSegment(BaseModel):
    """A single segment of the transcript."""

    start: float
    end: float
    text: str
    original_text: str | None = None
    speaker: str | None = None


class TranscriptData(BaseModel):
    """Full transcript data from API."""

    metadata: TranscriptMetadata
    segments: list[TranscriptSegment] = []
    text: str | None = None


class MindMapNode(BaseModel):
    """A node in the mind map."""

    node_id: str
    parent_node_id: str
    title: str
    color: str


class MindMapData(BaseModel):
    """Mind map structure."""

    nodes: list[MindMapNode] = []
    type: str = "flow"


class ActionItemAssignee(BaseModel):
    """Assignee info for action item."""

    label: str
    id: str | None = None


class ActionItem(BaseModel):
    """A single action item."""

    id: str
    label: str
    assignee: str | None = None
    context: str | None = None
    due_date: str | None = None
    priority: str = "medium"
    status: str = "TODO"
    is_completed: bool = False
    global_action_item_id: str | None = Field(
        None, validation_alias="globalActionItemId"
    )
    action_type: str | None = Field(None, validation_alias="type")
    payload: dict[str, Any] | None = None


class ActionItemsData(BaseModel):
    """Action items container."""

    actions: list[ActionItem] = []
    message: str | None = None


class SummarizationSummary(BaseModel):
    """AI-generated summary."""

    markdown: str = ""
    version: str = "1"


class SummarizationV2(BaseModel):
    """V2 summarization data."""

    summary: SummarizationSummary | None = None
    mind_map: MindMapData | None = Field(None, validation_alias="mindMap")
    action_items: ActionItemsData | None = Field(None, validation_alias="actionItems")


class SummarizationData(BaseModel):
    """A single summarization."""

    id: str = ""
    summarization_id: str = Field("", validation_alias="summarizationId")
    processing_status: str = Field("unknown", validation_alias="processingStatus")
    v2: SummarizationV2 | None = None
    created_at: str | None = Field(None, validation_alias="createdAt")
    updated_at: str | None = Field(None, validation_alias="updatedAt")


class HeyPocketRecording(BaseModel):
    """A single HeyPocket recording with all available data.

    All fields are optional to handle missing/empty API responses gracefully.
    """

    # Core fields
    id: str = ""
    title: str = "Untitled"
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime | None = None
    recording_at: datetime | None = None

    # Metadata
    duration: int | None = None
    state: str = "unknown"
    language: str = "en"
    description: str | None = None

    # Content
    transcript: TranscriptData | None = None
    raw_transcript: TranscriptData | None = None
    summarizations: dict[str, SummarizationData] = {}

    # Tags - can be strings or dicts with id/label
    tags: list[Any] = []

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: Any) -> list[Any]:
        """Normalize tags to list.

        Returns:
            List of normalized tags.
        """
        if not v:
            return []
        # Tags can be strings or dicts - normalize to list
        if isinstance(v, list):
            return v
        return [v]

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v: Any) -> datetime:
        """Parse datetime from string.

        Returns:
            Parsed datetime object.
        """
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.now()

    @field_validator("recording_at", mode="before")
    @classmethod
    def parse_recording_at(cls, v: Any) -> datetime | None:
        """Parse datetime from string.

        Returns:
            Parsed datetime object, or None if input is None.
        """
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return None

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_updated_at(cls, v: Any) -> datetime | None:
        """Parse datetime from string.

        Returns:
            Parsed datetime object, or None if input is None.
        """
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return None

    @property
    def plain_transcript(self) -> str | None:
        """Get plain text transcript, preferring raw_transcript."""
        if self.raw_transcript and self.raw_transcript.text:
            return self.raw_transcript.text
        if self.transcript and self.transcript.text:
            return self.transcript.text
        # Fallback: concatenate segments
        if self.transcript and self.transcript.segments:
            return "\n".join(s.text for s in self.transcript.segments)
        return None

    @property
    def markdown_summary(self) -> str | None:
        """Get markdown summary from first available summarization."""
        for s in self.summarizations.values():
            if s.v2 and s.v2.summary and s.v2.summary.markdown:
                return s.v2.summary.markdown
        return None

    @property
    def mind_map(self) -> MindMapData | None:
        """Get mind map from first available summarization."""
        for s in self.summarizations.values():
            if s.v2 and s.v2.mind_map:
                return s.v2.mind_map
        return None

    @property
    def action_items(self) -> list[ActionItem]:
        """Get action items from first available summarization."""
        for s in self.summarizations.values():
            if s.v2 and s.v2.action_items:
                return s.v2.action_items.actions
        return []

    @property
    def slug(self) -> str:
        """Generate a filesystem-safe slug from the title."""
        slug = self.title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")
