import os
from dotenv import load_dotenv

def load_environment():
    """
    Loads environment variables from .env file.
    Should be called once at framework initialization.
    """
    
    load_dotenv()

    # Optional validation (VERY useful in real frameworks)
    required_vars = ["BEEVO_URL"]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {missing}"
        )