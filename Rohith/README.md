1.Create Local Config File
Create this file (it is NOT stored in GitHub):
Rohith/config.py
Add:
import os
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = "Kubernetes"
REPO = "kubernetes"
DAYS = 10


2.Install Dependencies
pip install -r requirements.txt
