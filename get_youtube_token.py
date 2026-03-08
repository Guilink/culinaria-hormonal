"""
╔══════════════════════════════════════════════════════╗
║   GERADOR DE TOKEN YOUTUBE — Roda 1x no seu PC      ║
║   Gera o REFRESH_TOKEN para colocar na Railway       ║
╚══════════════════════════════════════════════════════╝

Como usar:
  1. Configure YOUTUBE_CLIENT_ID e YOUTUBE_CLIENT_SECRET no .env
  2. Execute: python get_youtube_token.py
  3. Autorize no navegador
  4. Copie o REFRESH_TOKEN exibido para as variáveis da Railway
"""

import os
import json
from pathlib import Path

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

client_id     = os.environ.get("YOUTUBE_CLIENT_ID", "")
client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

if not client_id or not client_secret:
    print("❌ Configure YOUTUBE_CLIENT_ID e YOUTUBE_CLIENT_SECRET no arquivo .env")
    exit(1)

# Monta o config no formato que o google espera
client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

print("\n" + "="*60)
print("✅ TOKEN GERADO COM SUCESSO!")
print("="*60)
print(f"\nYOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
print("\n📋 Copie a linha acima e adicione nas variáveis da Railway")
print("="*60 + "\n")