import os


class Settings:
    # Beevo API
    BEEVO_URL = os.getenv(
        "BEEVO_URL",
        "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT"
    )

    BEEVO_TOKEN = os.getenv("BEEVO_TOKEN")
    BEEVO_COOKIE = os.getenv("BEEVO_COOKIE")

    # Default language
    LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt_PT")

    # Optional environment mode
    ENV = os.getenv("ENV", "development")

    @classmethod
    def is_production(cls):
        return cls.ENV == "production"