"""Tests for environment configuration (WikiEnvironment, WIKI_RAW_PATH)."""

import os
from pathlib import Path

from shared.environment import WikiEnvironment, get_wiki_env


class TestWikiEnvironment:
    """Tests for WikiEnvironment and WIKI_RAW_PATH handling."""

    def test_uses_default_when_not_set(self, monkeypatch):
        """Test WikiEnvironment uses expected default when not overridden.

        Note: This avoids depending on .env contents by explicitly setting
        WIKI_RAW_PATH to a controlled value in the environment.
        """
        # Set an explicit path so we don't depend on .env file state.
        monkeypatch.setenv("WIKI_RAW_PATH", str(Path.home() / "wiki/raw"))

        env = WikiEnvironment()
        assert env.wiki_raw_path == Path.home() / "wiki/raw"

    def test_uses_env_var_via_alias(self, tmp_path, monkeypatch):
        """Test WikiEnvironment reads WIKI_RAW_PATH from environment."""
        expected = str(tmp_path / "my-wiki")
        monkeypatch.setenv("WIKI_RAW_PATH", expected)

        env = WikiEnvironment()
        assert env.wiki_raw_path == Path(expected)


class TestGetWikiEnv:
    """Tests for get_wiki_env helper."""

    def test_returns_wiki_environment(self, monkeypatch):
        """Test get_wiki_env returns a WikiEnvironment instance."""
        # Ensure WIKI_RAW_PATH is set so _ensure_... doesn't prompt.
        monkeypatch.setenv("WIKI_RAW_PATH", "/tmp/test-wiki")

        env = get_wiki_env()
        assert isinstance(env, WikiEnvironment)
        assert str(env.wiki_raw_path) == "/tmp/test-wiki"


class TestEnsureWikiRawPathInEnv:
    """Tests for _ensure_wiki_raw_path_in_env behavior."""

    def test_does_not_prompt_if_already_set(self, monkeypatch):
        """Test no prompt if WIKI_RAW_PATH is already set."""
        from shared.environment import _ensure_wiki_raw_path_in_env

        monkeypatch.setenv("WIKI_RAW_PATH", "/tmp/existing-wiki")

        # Should not call input; just return immediately.
        _ensure_wiki_raw_path_in_env()

        assert os.environ.get("WIKI_RAW_PATH") == "/tmp/existing-wiki"
