import os

class Config:
    """
    Central configuration for Beevo API framework.
    Reads values from environment variables.
    """
    
    BEEVO_URL = os.getenv("BEEVO_URL")
    ENV = os.getenv("ENV", "dev")
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"