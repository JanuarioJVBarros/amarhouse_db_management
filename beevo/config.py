from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    BEEVO_URL = os.getenv("BEEVO_URL")
    BEEVO_COOKIE = os.getenv("BEEVO_COOKIE")