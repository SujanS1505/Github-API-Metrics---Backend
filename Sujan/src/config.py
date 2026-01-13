import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = "https://api.github.com"

if not GITHUB_TOKEN:
    raise RuntimeError("GitHub token not found")
