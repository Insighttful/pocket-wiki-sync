"""Wiki output module — save HeyPocket recordings to local wiki format.

Follows the LLM Wiki skill conventions for markdown structure, frontmatter,
and wikilinks. Recordings are saved directly under WIKI_RAW_PATH as:
    <YYYY-MM-DD>-<slug>.md

Each recording produces a single markdown file with YAML frontmatter containing:
- id, title, created, recording_at, duration, state, language, tags
- transcript (plain text)
- summary (markdown from AI)
- mind_map (structured nodes)
- action_items (list with label, assignee, context, due_date, priority, status)
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from shared.environment import WikiEnvironment
from shared.pocket.models import HeyPocketRecording

logger = logging.getLogger(__name__)


class WikiOutput:
    """Save HeyPocket recordings to a local wiki following LLM Wiki conventions."""

    def __init__(self, env: WikiEnvironment):
        self.env = env
        # WIKI_RAW_PATH is exactly where transcripts are saved.
        self.base_path = env.wiki_raw_path

    def ensure_directories(self) -> None:
        """Create the transcripts directory if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured wiki directories exist")

    def save_recording(self, recording: HeyPocketRecording) -> Path | None:
        """Save a single HeyPocket recording to the wiki.

        Returns the path where the file was saved, or None if skipped.

        Returns:
            Path to the saved file, or None if the recording was skipped.
        """
        # Use plain_transcript from raw_transcript
        transcript = recording.plain_transcript
        if not transcript:
            logger.warning("Skipping recording without transcript: %s", recording.title)
            return None

        # Generate filename following wiki conventions
        timestamp = recording.created_at.strftime("%Y-%m-%d")
        slug = recording.slug
        filename = f"{timestamp}-{slug}.md"
        filepath = self.base_path / filename

        # Skip if already exists (idempotent sync)
        if filepath.exists():
            logger.debug("Recording already exists, skipping: %s", filepath.name)
            return None

        # Generate markdown content
        content = self._format_recording(recording, filepath.name)

        # Write file
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        logger.info("Saved recording: %s (%s)", filepath.name, recording.title)

        return filepath

    def _format_recording(self, recording: HeyPocketRecording, filename: str) -> str:
        """Format recording as markdown with frontmatter and body sections.

        Frontmatter: metadata only (id, title, created, recording_at,
        duration, state, language, tags)
        Body: transcript, summary, mind_map, action_items as markdown sections

        Returns:
            Formatted markdown string.
        """
        # Build frontmatter with all available metadata
        frontmatter: dict[str, Any] = {
            "id": recording.id,
            "title": recording.title,
            "created": recording.created_at.isoformat(),
            "updated": recording.updated_at.isoformat()
            if recording.updated_at
            else None,
            "recording_at": recording.recording_at.isoformat()
            if recording.recording_at
            else None,
            "duration_seconds": recording.duration,
            "state": recording.state,
            "language": recording.language,
            "description": recording.description,
            "tags": self._normalize_tags(recording.tags),
        }

        # Filter out None values and empty tags from frontmatter
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
        if frontmatter.get("tags") == []:
            del frontmatter["tags"]

        # Add transcript metadata
        if recording.transcript and recording.transcript.metadata:
            meta = recording.transcript.metadata
            frontmatter["transcript_metadata"] = {
                "duration": meta.duration,
                "language": meta.language,
                "language_probability": meta.language_probability,
                "source": meta.source,
            }

        # Generate YAML frontmatter
        yaml_content = yaml.dump(
            frontmatter,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Build markdown body with sections
        lines = [
            "---",
            yaml_content.rstrip(),
            "---",
            "",
            f"# {recording.title}",
            "",
        ]

        # Summary (markdown from AI)
        if recording.markdown_summary:
            lines.extend(
                [
                    "## Summary",
                    recording.markdown_summary,
                    "",
                ]
            )

        # Mind map (structured nodes)
        if recording.mind_map and recording.mind_map.nodes:
            lines.append("## Mind Map")
            lines.append("")
            lines.append(f"Type: {recording.mind_map.type}")
            lines.append("")
            lines.append("### Nodes")
            lines.append("")
            for node in recording.mind_map.nodes:
                lines.append(f"- **{node.title}**")
                lines.append(f"  - id: {node.node_id}")
                lines.append(f"  - parent_id: {node.parent_node_id or ''}")
                lines.append(f"  - color: {node.color}")
            lines.append("")

        # Action items
        lines.extend(self._format_action_items(recording))

        # Transcript (plain text) - last section
        if recording.plain_transcript:
            lines.extend(
                [
                    "## Transcript",
                    recording.plain_transcript,
                ]
            )

        return "\n".join(lines)

    def _normalize_tags(self, tags: list[Any]) -> list[str]:
        """Normalize tags to list of strings.

        Returns:
            List of normalized tag strings.
        """
        result = []
        for tag in tags:
            if isinstance(tag, str):
                result.append(tag)
            elif isinstance(tag, dict):
                # Tag dict has 'name' field, fallback to 'id' or 'label'
                result.append(
                    tag.get("name", tag.get("label", tag.get("id", str(tag))))
                )
            else:
                result.append(str(tag))
        return result

    def _format_action_items(self, recording: HeyPocketRecording) -> list[str]:
        """Format action items section of the recording markdown.

        Returns:
            List of markdown lines for the action items section.
        """
        if not recording.action_items:
            return []
        lines = ["## Action Items", ""]
        for item in recording.action_items:
            status_icon = "x" if item.is_completed else " "
            lines.append(f"- [{status_icon}] **{item.label}**")
            lines.append(f"  - id: {item.id}")
            if item.assignee:
                lines.append(f"  - assignee: {item.assignee}")
            if item.context:
                lines.append(f"  - context: {item.context}")
            if item.due_date:
                lines.append(f"  - due_date: {item.due_date}")
            if item.priority:
                lines.append(f"  - priority: {item.priority}")
            if item.status:
                lines.append(f"  - status: {item.status}")
            if item.global_action_item_id:
                lines.append(f"  - global_action_item_id: {item.global_action_item_id}")
            if item.action_type:
                lines.append(f"  - type: {item.action_type}")
        lines.append("")
        return lines
