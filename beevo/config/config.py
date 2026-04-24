import os
from dataclasses import dataclass

from beevo.exceptions import BeevoConfigurationError


@dataclass(frozen=True)
class BeevoSettings:
    beevo_url: str
    beevo_cookie: str
    env: str = "dev"
    request_timeout: int = 30
    debug: bool = False

    @classmethod
    def from_env(cls, validate=True):
        settings = cls(
            beevo_url=os.getenv("BEEVO_URL", ""),
            beevo_cookie=os.getenv("BEEVO_COOKIE", ""),
            env=os.getenv("ENV", "dev"),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", 30)),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

        if validate:
            settings.validate()

        return settings

    def validate(self):
        missing = []

        if not self.beevo_url:
            missing.append("BEEVO_URL")

        if not self.beevo_cookie:
            missing.append("BEEVO_COOKIE")

        if missing:
            raise BeevoConfigurationError(
                f"Missing required environment variables: {missing}"
            )

        if self.request_timeout <= 0:
            raise BeevoConfigurationError("REQUEST_TIMEOUT must be greater than zero")


def get_settings(validate=True):
    return BeevoSettings.from_env(validate=validate)
