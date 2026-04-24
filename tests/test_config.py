import pytest

from beevo.config.config import BeevoSettings, get_settings
from beevo.exceptions import BeevoConfigurationError


def test_from_env_builds_settings_from_environment(monkeypatch):
    monkeypatch.setenv("BEEVO_URL", "https://example.test/graphql")
    monkeypatch.setenv("BEEVO_COOKIE", "session=abc")
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("REQUEST_TIMEOUT", "45")
    monkeypatch.setenv("DEBUG", "true")

    settings = BeevoSettings.from_env()

    assert settings.beevo_url == "https://example.test/graphql"
    assert settings.beevo_cookie == "session=abc"
    assert settings.env == "staging"
    assert settings.request_timeout == 45
    assert settings.debug is True


def test_validate_raises_when_required_values_are_missing():
    settings = BeevoSettings(beevo_url="", beevo_cookie="")

    with pytest.raises(BeevoConfigurationError, match="Missing required environment variables"):
        settings.validate()


def test_validate_raises_for_non_positive_timeout():
    settings = BeevoSettings(
        beevo_url="https://example.test/graphql",
        beevo_cookie="session=abc",
        request_timeout=0,
    )

    with pytest.raises(BeevoConfigurationError, match="REQUEST_TIMEOUT must be greater than zero"):
        settings.validate()


def test_get_settings_delegates_to_environment(monkeypatch):
    monkeypatch.setenv("BEEVO_URL", "https://example.test/graphql")
    monkeypatch.setenv("BEEVO_COOKIE", "session=abc")

    settings = get_settings()

    assert settings.beevo_url == "https://example.test/graphql"
    assert settings.beevo_cookie == "session=abc"
