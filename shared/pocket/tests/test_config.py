"""Tests for shared/pocket/config.py."""

from unittest.mock import MagicMock, patch

from shared.pocket.config import HeyPocketConfig


class TestHeyPocketConfig:
    """Tests for HeyPocketConfig."""

    @patch("shared.pocket.config.get_heypocket_env")
    def test_from_environment(self, mock_env):
        """Test loading config from environment."""
        mock_env.return_value = MagicMock(
            heypocket_api_key="pk_test123",
            heypocket_base_url="https://test.heypocketai.com/api/v1",
            heypocket_max_retries=5,
            heypocket_max_concurrent=10,
        )

        config = HeyPocketConfig.from_environment()

        assert config.api_key == "pk_test123"
        assert config.base_url == "https://test.heypocketai.com/api/v1"
        assert config.max_retries == 5
        assert config.max_concurrent == 10

    def test_default_values(self):
        """Test default values when not from environment."""
        config = HeyPocketConfig(api_key="pk_test")

        assert config.api_key == "pk_test"
        assert config.base_url == "https://public.heypocketai.com/api/v1"
        assert config.max_retries == 3
        assert config.max_concurrent == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HeyPocketConfig(
            api_key="pk_custom",
            base_url="https://custom.api.com/v1",
            max_retries=10,
            max_concurrent=5,
        )

        assert config.api_key == "pk_custom"
        assert config.base_url == "https://custom.api.com/v1"
        assert config.max_retries == 10
        assert config.max_concurrent == 5
