FROM python:3.11-slim

# Instala FFmpeg + fontes com suporte a acentos + dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependências primeiro (cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY main.py .
COPY scheduler.py .
COPY test_now.py .
COPY get_youtube_token.py .

# Copia os assets (logo, fontes, vídeos de fundo, músicas)
COPY assets/ ./assets/
COPY bg_videos/ ./bg_videos/
COPY music/ ./music/

# Cria pastas de saída
RUN mkdir -p output

# O scheduler roda continuamente
CMD ["python", "scheduler.py"]