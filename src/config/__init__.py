# Config package initialization
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")
EMAIL_STORAGE_PATH = os.path.join(DATA_DIR, "emails")
PROCESSED_EMAILS_DIR = os.path.join(EMAIL_STORAGE_PATH, "processed_emails")

# Create directories if they don't exist
os.makedirs(EMAIL_STORAGE_PATH, exist_ok=True)
os.makedirs(PROCESSED_EMAILS_DIR, exist_ok=True)