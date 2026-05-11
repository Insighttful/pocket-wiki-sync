"""Configuration for HeyPocket AI API connection."""

from pydantic import BaseModel

from shared.environment import get_heypocket_env


class HeyPocketConfig(BaseModel):
    """Configuration for HeyPocket AI API connection."""

    api_key: str
    base_url: str = "https://public.heypocketai.com/api/v1"
    max_retries: int = 3
    max_concurrent: int = 3

    @classmethod
    def from_environment(cls) -> "HeyPocketConfig":
        """Load configuration from environment.

        Returns:
            HeyPocketConfig instance.
        """
        env = get_heypocket_env()
        return cls(
            api_key=env.heypocket_api_key,
            base_url=env.heypocket_base_url,
            max_retries=env.heypocket_max_retries,
            max_concurrent=env.heypocket_max_concurrent,
        )
