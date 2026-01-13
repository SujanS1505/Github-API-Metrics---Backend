import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    
    @staticmethod
    def get_github_token():
        return Config.GITHUB_TOKEN

    @staticmethod
    def get_output_dir():
        return Config.OUTPUT_DIR
