from config import Config

class Auth:
    @staticmethod
    def get_github_token():
        token = Config.get_github_token()
        if not token:
            raise ValueError("GITHUB_TOKEN not found in environment variables.")
        return token
