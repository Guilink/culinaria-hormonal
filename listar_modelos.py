from google import genai
import os

for line in open('.env', encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('=')
        os.environ[k.strip()] = v.strip()

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

print("Modelos de IMAGEM disponíveis:\n")
for m in client.models.list():
    if 'generateImages' in (m.supported_actions or []) or 'imagen' in m.name.lower():
        print(m.name, '|', m.supported_actions)