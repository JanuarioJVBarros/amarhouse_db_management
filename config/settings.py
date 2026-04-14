import os


class Settings:
    # Beevo API
    BEEVO_URL = os.getenv(
        "BEEVO_URL",
        "https://amarhouse.beevo.com/admin-api"
    )

    BEEVO_TOKEN = os.getenv("BEEVO_TOKEN", "ntu5xliv95as4zhifv1c")
    BEEVO_COOKIES = ("locale=pt_PT; "
                     "beevo-admin=eyJ0b2tlbiI6IjJkMDAyODkx...; "
                     "beevo-admin.sig=uE7aVkWmaR5X_ov1JsoyzOd4BW8")

    # Default language
    LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt_PT")

    # Optional environment mode
    ENV = os.getenv("ENV", "development")

    @classmethod
    def is_production(cls):
        return cls.ENV == "production"