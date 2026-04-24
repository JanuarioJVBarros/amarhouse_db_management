from dotenv import load_dotenv

from beevo.config.config import get_settings

def load_environment():
    """
    Loads environment variables from .env file.
    Should be called once at framework initialization.
    """

    load_dotenv()
    return get_settings(validate=True)
