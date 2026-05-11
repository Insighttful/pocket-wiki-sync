"""Wiki output module — save HeyPocket recordings to local wiki format.

Follows the LLM Wiki skill conventions for markdown structure, frontmatter,
and wikilinks. Recordings are saved under the configured wiki path in a
dedicated 'pocket' subdirectory structure.

Directory layout:
    <WIKI_PATH>/
        raw/
            pocket/
                <YYYY-MM-DD>-<slug>.md  (single file per recording with all subtypes)
        concepts/
            pocket-sources.md           (index of all sources)
        queries/
            pocket-sync-YYYY-MM-DD.md   (sync log entry)

Each recording produces a single markdown file with YAML frontmatter containing:
- id, title, created, recording_at, duration, state, language, tags
- transcript (plain text)
- summary (markdown from AI)
- mind_map (structured nodes)
- action_items (list with label, assignee, context, due_date, priority, status)
"""

import logging
from datetime import UTC, datetime
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
        self.base_path = env.wiki_path / "raw" / "pocket"
        self.concepts_path = env.wiki_path / "concepts"
        self.queries_path = env.wiki_path / "queries"

    def ensure_directories(self) -> None:
        """Create all required wiki directories if they don't exist."""
        for path in [self.base_path, self.concepts_path, self.queries_path]:
            path.mkdir(parents=True, exist_ok=True)
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

    def update_sources_index(self, recordings: list[HeyPocketRecording]) -> None:
        """Update the sources index in concepts/ directory."""
        index_path = self.concepts_path / "pocket-sources.md"
        created = datetime.now(UTC).strftime("%Y-%m-%d")

        lines = [
            "---",
            "title: Pocket Sources Index",
            "created: " + created,
            "updated: " + created,
            "type: entity",
            "tags: [pocket, sources, collection]",
            "---",
            "",
            "# Pocket Sources Index",
            "",
            "> Index of all HeyPocket recordings synced to this wiki.",
            "> Auto-generated — do not edit manually.",
            "",
            "## Recordings",
            "",
        ]

        for recording in sorted(recordings, key=lambda r: r.title.lower()):
            slug = recording.slug
            lines.append(f"- [[pocket/{slug}|{recording.title}]]")

        lines.append("")
        lines.append(
            "*Last updated: " + datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC") + "*"
        )
        lines.append("")

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Updated sources index: %s", index_path.name)

    def create_sync_log(self, recordings: list[HeyPocketRecording]) -> None:
        """Create a sync log entry in queries/ directory."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        log_path = self.queries_path / f"pocket-sync-{date_str}.md"

        # Don't overwrite existing logs
        if log_path.exists():
            logger.debug("Sync log already exists for %s, appending", date_str)
            content = log_path.read_text(encoding="utf-8")
            if "## Synced Recordings" in content:
                # Append to existing section
                content = content.replace(
                    "## Synced Recordings",
                    "## Synced Recordings\n\n### "
                    + now.strftime("%H:%M UTC")
                    + " sync",
                )
                for recording in recordings:
                    content += f"\n- {recording.title}"
            else:
                # Add new section at end
                sync_time = now.strftime("%H:%M UTC")
                content += f"\n\n## Synced Recordings\n\n### {sync_time} sync\n\n"
                for recording in recordings:
                    content += f"- {recording.title}\n"
            log_path.write_text(content, encoding="utf-8")
            return

        # Create new log file
        created = now.strftime("%Y-%m-%d")
        lines = [
            "---",
            "title: Pocket Sync Log - " + date_str,
            "created: " + created,
            "updated: " + created,
            "type: query",
            "tags: [pocket, sync, log]",
            "---",
            "",
            "# Pocket Sync Log - " + date_str,
            "",
            "> Automated sync log — generated by pocket-wiki-sync",
            "",
            "## Synced Recordings",
            "",
        ]

        lines.extend(f"- {recording.title}" for recording in recordings)

        lines.append("")
        lines.append(f"*Total recordings synced: {len(recordings)}*")
        lines.append("")

        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Created sync log: %s", log_path.name)
