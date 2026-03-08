"""
╔══════════════════════════════════════════════════════╗
║        CULINÁRIA HORMONAL - Gerador Automático       ║
║  Gera receita → imagens → layout → vídeo completo   ║
║  + Upload automático para YouTube                    ║
╚══════════════════════════════════════════════════════╝
"""

import os
import json
import random
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ─── CONFIGURAÇÕES ────────────────────────────────────────────────────────────

def load_env():
    """Carrega .env sem depender de python-dotenv."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

IMAGEN_MODEL = "imagen-4.0-fast-generate-001"

BASE_DIR      = Path(__file__).parent
ASSETS_DIR    = BASE_DIR / "assets"
BG_VIDEOS_DIR = BASE_DIR / "bg_videos"
MUSIC_DIR     = BASE_DIR / "music"
OUTPUT_DIR    = BASE_DIR / "output"
HISTORY_FILE  = BASE_DIR / "historico_receitas.json"

CANVAS_W = 1080
CANVAS_H = 1920

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

from PIL import Image, ImageDraw, ImageFont
import io

# ─── HISTÓRICO ────────────────────────────────────────────────────────────────

def carregar_historico() -> list:
    if HISTORY_FILE.exists():
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data.get("titulos", [])
    return []

def salvar_historico(titulo: str):
    historico = carregar_historico()
    historico.append(titulo)
    historico = historico[-200:]
    HISTORY_FILE.write_text(
        json.dumps({"titulos": historico}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ─── GERAÇÃO DE RECEITA ───────────────────────────────────────────────────────

def gerar_receita(historico: list) -> dict:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    historico_str = "\n".join(f"- {t}" for t in historico[-50:]) or "Nenhuma ainda."

    prompt = f"""Você é especialista em conteúdo para o canal "Culinária Hormonal" no YouTube.
O canal vende o infoproduto "Reset Hormonal em 7 Dias" para mulheres 40+.
O público sofre com: ganho de peso, inchaço, insônia, fadiga, fogachos, humor instável.

RECEITAS JÁ PUBLICADAS (NÃO REPITA NENHUMA):
{historico_str}

TAREFA: Crie UMA receita NOVA, saudável, simples e barata.
Use ingredientes anti-inflamatórios que equilibram hormônios e são fáceis de encontrar.
A receita pode ser lanches rápidos, cafés, sobremesa, almoço, janta, etc...

═══ REGRAS DO TÍTULO ═══

- Máximo 65 caracteres
- Tom de descoberta / curiosidade (algo que poucas pessoas sabem)
- Frase curta e direta (estilo Shorts viral)
- Priorizar estruturas como:

  • "Poucos sabem o poder desse..."
  • "O ___ que..."
  • "Esse ___ que..."
  • "Troquei ___ por isso e..."
  • "O ___ que faço em X minutos"
  • "O ___ que mudou meu café da manhã"
  • "Esse ___ que espanta o cansaço"
  • "O ___ que ajuda a dormir"
  • "Esse ___ que revolucionou minha ___"

- Use gatilhos de curiosidade e benefício:
  poder, segredo, espanta, energia, memória, sono, cansaço,
  diferente, revolucionou, troquei, que poucos conhecem

- NÃO usar títulos longos ou explicativos demais
- Priorizar curiosidade + benefício

═══ REGRAS DA DESCRIÇÃO DO CARD (aparece no vídeo) ═══

- 4–5 frases curtas
- Primeira frase: conectar com um problema comum
- Segunda e terceira frases: ingredientes e modo de preparo de forma sucinta
- Quarta frase: mencionar benefícios naturais do alimento
- Linguagem simples e natural (parecendo dica de amiga)
- O fim da descrição deve ser EXATAMENTE: "(LEIA A DESCRIÇÃO)"

═══ REGRAS DA DESCRIÇÃO DO YOUTUBE (bio do vídeo) ═══
- Abre com frase emocional forte conectada a sintomas hormonais
- 2-3 frases ligando a receita ao Reset Hormonal
- Tom: amiga próxima, empática, sem julgamento
- Fecha EXATAMENTE com: "👉 PARA ACESSAR: Toque no nome do canal (no vídeo) e depois no LINK que está no perfil. Faça esse favor para si mesma..."

═══ REGRAS DOS PROMPTS DE IMAGEM ═══
- Em inglês, fotorrealistas, para geração por IA
- prompt_ingredientes: mise en place com quantidades exatas da receita
- prompt_prato_pronto: hero shot apetitoso do prato finalizado

Responda SOMENTE em JSON válido, sem markdown, sem texto extra:
{{
  "titulo": "...",
  "descricao_card": "...",
  "descricao_youtube": "...",
  "prompt_ingredientes": "...",
  "prompt_prato_pronto": "..."
}}"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ─── GERAÇÃO DE IMAGENS ───────────────────────────────────────────────────────

def gerar_imagens(prompt_ingredientes: str, prompt_prato: str):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)

    prefixo = "Professional food photography, cinematic lighting, ultra-realistic, beautiful composition: "
    sufixo_hero = ", vibrant colors, appetizing, steam rising, mouth-watering hero shot"

    def gerar(prompt: str, extra: str = "") -> Image.Image:
        resultado = client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prefixo + prompt + extra,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            )
        )
        img_bytes = resultado.generated_images[0].image.image_bytes
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    print("  🖼️  Gerando imagem 1 (ingredientes)...")
    img1 = gerar(prompt_ingredientes)
    print("  🖼️  Gerando imagem 2 (prato pronto)...")
    img2 = gerar(prompt_prato, sufixo_hero)

    return img1, img2

# ─── MONTAGEM DO LAYOUT ───────────────────────────────────────────────────────

def arredondar_cantos(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    result = img.copy().convert("RGBA")
    result.putalpha(mask)
    return result

def quebrar_texto(draw: ImageDraw.Draw, texto: str, fonte, max_w: int) -> list:
    linhas = []
    for paragrafo in texto.split("\n"):
        if not paragrafo.strip():
            linhas.append("")
            continue
        palavras = paragrafo.split()
        linha_atual = ""
        for palavra in palavras:
            teste = (linha_atual + " " + palavra).strip()
            bb = draw.textbbox((0, 0), teste, font=fonte)
            if bb[2] - bb[0] <= max_w:
                linha_atual = teste
            else:
                if linha_atual:
                    linhas.append(linha_atual)
                linha_atual = palavra
        if linha_atual:
            linhas.append(linha_atual)
    return linhas


def montar_layout(receita: dict, img_ingredientes: Image.Image, img_prato: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def carregar_fonte_win(bold: bool, tamanho: int):
        nomes = ["arialbd.ttf", "Arial_Bold.ttf"] if bold else ["arial.ttf", "Arial.ttf"]
        fallbacks = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
        for nome in nomes + fallbacks:
            caminhos = [
                Path(f"C:/Windows/Fonts/{nome}"),
                ASSETS_DIR / "fonts" / nome,
                Path(f"/usr/share/fonts/truetype/dejavu/{nome}"),
            ]
            for c in caminhos:
                if c.exists():
                    return ImageFont.truetype(str(c), tamanho)
        return ImageFont.load_default(size=tamanho)

    fonte_titulo = carregar_fonte_win(bold=True, tamanho=52)
    fonte_desc   = carregar_fonte_win(bold=True, tamanho=42)

    CORNER_R = 28
    DESC_PAD = 40

    TITULO_Y     = 180
    titulo_max_w = CANVAS_W - 110 * 2
    titulo_lh    = int(52 * 1.18)

    IMGS_Y = 380
    IMGS_W = CANVAS_W
    IMGS_H = IMGS_W // 2

    LOGO_Y    = 800
    logo_size = 115

    DESC_X = 40
    DESC_W = 830
    DESC_Y = IMGS_Y + IMGS_H + 20

    linhas_titulo = quebrar_texto(draw, receita["titulo"].upper(), fonte_titulo, titulo_max_w)

    for i, linha in enumerate(linhas_titulo):
        bb = draw.textbbox((0, 0), linha, font=fonte_titulo)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]
        tx = (CANVAS_W - lw) // 2
        ty = TITULO_Y + i * titulo_lh

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        pad = 20
        ov_draw.rounded_rectangle(
            [(tx - pad, ty - pad // 2), (tx + lw + pad, ty + lh + pad // 2)],
            radius=14, fill=(255, 255, 255, 235)
        )
        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)
        draw.text((tx, ty), linha, font=fonte_titulo, fill=(15, 15, 15, 255))

    img_w = IMGS_W // 2
    img_h = IMGS_H

    img1_rs = img_ingredientes.resize((img_w, img_h), Image.LANCZOS)
    img2_rs = img_prato.resize((img_w, img_h), Image.LANCZOS)
    img1_rd = arredondar_cantos(img1_rs, CORNER_R)
    img2_rd = arredondar_cantos(img2_rs, CORNER_R)

    canvas.paste(img1_rd, (0, IMGS_Y), img1_rd)
    canvas.paste(img2_rd, (img_w, IMGS_Y), img2_rd)

    linhas_desc = quebrar_texto(draw, receita["descricao_card"], fonte_desc,
                                DESC_W - DESC_PAD * 2)
    desc_lh    = int(42 * 1.35)
    desc_box_h = len(linhas_desc) * desc_lh + DESC_PAD * 2

    overlay3 = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ov3_draw = ImageDraw.Draw(overlay3)
    ov3_draw.rounded_rectangle(
        [(DESC_X, DESC_Y), (DESC_X + DESC_W, DESC_Y + desc_box_h)],
        radius=28, fill=(255, 255, 255, 248)
    )
    canvas = Image.alpha_composite(canvas, overlay3)
    draw = ImageDraw.Draw(canvas)

    for i, linha in enumerate(linhas_desc):
        ty = DESC_Y + DESC_PAD + i * desc_lh
        draw.text((DESC_X + DESC_PAD, ty), linha,
                  font=fonte_desc, fill=(15, 15, 15, 255))

    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        logo_raw = Image.open(logo_path).convert("RGBA").resize((logo_size, logo_size), Image.LANCZOS)

        mask_circle = Image.new("L", (logo_size, logo_size), 0)
        ImageDraw.Draw(mask_circle).ellipse([(0, 0), (logo_size, logo_size)], fill=255)

        logo_bg = Image.new("RGBA", (logo_size, logo_size), (255, 255, 255, 255))
        logo_bg.putalpha(mask_circle)

        logo_final = Image.alpha_composite(logo_bg, logo_raw)
        lx = (CANVAS_W - logo_size) // 2
        canvas.paste(logo_final, (lx, LOGO_Y), mask_circle)

    return canvas


# ─── DURAÇÃO DO ÁUDIO (FFprobe) ───────────────────────────────────────────────

def obter_duracao_audio(caminho: Path) -> float:
    """Retorna duração em segundos do arquivo de áudio usando ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(caminho)
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(resultado.stdout.strip())
    except ValueError:
        return 97.0  # fallback: 1:37 min


# ─── MONTAGEM DO VÍDEO (FFMPEG) ───────────────────────────────────────────────

def verificar_ffmpeg():
    import shutil
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg não encontrado!\n"
            "Instale em: https://www.gyan.dev/ffmpeg/builds/\n"
            "Baixe 'ffmpeg-release-essentials.zip', extraia e adicione a pasta bin ao PATH."
        )

def montar_video(frame_png: Path, titulo: str) -> Path:
    """
    Combina vídeo de fundo (loop 6s) + frame PNG + trecho ALEATÓRIO de 6s do áudio → .mp4
    """
    verificar_ffmpeg()

    DURACAO = 6

    videos_bg = list(BG_VIDEOS_DIR.glob("*.mp4"))
    if not videos_bg:
        raise FileNotFoundError(
            f"Nenhum .mp4 encontrado em '{BG_VIDEOS_DIR}'.\n"
            "Adicione pelo menos um vídeo de fundo nessa pasta."
        )

    musicas = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a"))
    if not musicas:
        raise FileNotFoundError(
            f"Nenhuma música encontrada em '{MUSIC_DIR}'.\n"
            "Adicione arquivos .mp3 ou .m4a nessa pasta."
        )

    bg_path     = random.choice(videos_bg)
    musica_path = random.choice(musicas)

    # ── TRECHO ALEATÓRIO DO ÁUDIO ─────────────────────────────────────────
    duracao_audio = obter_duracao_audio(musica_path)
    # Garante que o trecho de 6s cabe dentro da música (com 1s de margem no fim)
    max_inicio = max(0.0, duracao_audio - DURACAO - 1.0)
    inicio_audio = round(random.uniform(0.0, max_inicio), 2)

    print(f"  🎬 Fundo  : {bg_path.name}")
    print(f"  🎵 Música : {musica_path.name}")
    print(f"  ⏱️  Trecho : {inicio_audio:.1f}s → {inicio_audio + DURACAO:.1f}s "
          f"(de {duracao_audio:.1f}s totais)")

    nome = (titulo[:40].replace(" ", "_")
                       .replace("/", "-")
                       .replace("'", "")
            + "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4")
    saida = OUTPUT_DIR / nome

    # -ss antes de -i no áudio = seek rápido (sem redecodificar tudo)
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(bg_path),
        "-loop", "1",          "-i", str(frame_png),
        "-ss", str(inicio_audio), "-stream_loop", "-1", "-i", str(musica_path),
        "-filter_complex",
        (
            f"[0:v]scale={CANVAS_W}:{CANVAS_H},setsar=1[bg];"
            f"[1:v]scale={CANVAS_W}:{CANVAS_H}[overlay];"
            f"[bg][overlay]overlay=0:0[v];"
            f"[2:a]volume=0.4,afade=t=out:st={DURACAO-1}:d=1[a]"
        ),
        "-map", "[v]",
        "-map", "[a]",
        "-t", str(DURACAO),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(saida)
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Erro no FFmpeg:\n{resultado.stderr[-500:]}")

    return saida


# ─── UPLOAD PARA O YOUTUBE ────────────────────────────────────────────────────

def upload_youtube(video_path: Path, titulo: str, descricao: str) -> str:
    """
    Faz upload do vídeo para o YouTube como Short (não listado por padrão).
    Retorna o ID do vídeo publicado.
    """
    import google.oauth2.credentials
    import googleapiclient.discovery
    import googleapiclient.http

    # Credenciais OAuth2 via variáveis de ambiente (Railway)
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("YOUTUBE_CLIENT_ID", ""),
        client_secret=os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
    )

    youtube = googleapiclient.discovery.build(
        "youtube", "v3",
        credentials=creds,
        cache_discovery=False
    )

    body = {
        "snippet": {
            "title": titulo,
            "description": descricao,
            "tags": [
                "culinária hormonal", "receitas saudáveis", "saúde feminina",
                "menopausa", "hormônios", "emagrecer", "shorts", "receitasaudavel"
            ],
            "categoryId": "26",   # Howto & Style
            "defaultLanguage": "pt",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = googleapiclient.http.MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print("  📤 Enviando para YouTube...", end="", flush=True)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"\r  📤 Upload: {pct}%", end="", flush=True)

    print(f"\r  📤 Upload: 100% ✅")
    video_id = response.get("id", "")
    print(f"  🔗 https://youtube.com/shorts/{video_id}")
    return video_id


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def gerar_e_postar() -> dict:
    """Pipeline completo: receita → imagens → layout → vídeo → YouTube."""

    print("\n" + "═"*54)
    print("  🌿 CULINÁRIA HORMONAL — Gerador Automático")
    print("═"*54)

    for pasta in [OUTPUT_DIR, ASSETS_DIR, BG_VIDEOS_DIR, MUSIC_DIR]:
        pasta.mkdir(parents=True, exist_ok=True)

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY não encontrada. Configure o arquivo .env")

    # 1. Receita
    print("\n📝 [1/5] Gerando receita...")
    historico = carregar_historico()
    print(f"         Histórico: {len(historico)} receitas já publicadas")
    receita = gerar_receita(historico)
    print(f"         ✅ {receita['titulo']}")

    # 2. Imagens
    print("\n🖼️  [2/5] Gerando imagens...")
    img_ingredientes, img_prato = gerar_imagens(
        receita["prompt_ingredientes"],
        receita["prompt_prato_pronto"]
    )
    print("         ✅ Imagens geradas")

    # 3. Layout
    print("\n🎨 [3/5] Montando layout...")
    frame = montar_layout(receita, img_ingredientes, img_prato)
    frame_tmp = OUTPUT_DIR / "_frame_temp.png"
    frame.save(str(frame_tmp), "PNG")
    print("         ✅ Layout pronto")

    # 4. Vídeo
    print("\n🎬 [4/5] Montando vídeo final...")
    video_path = montar_video(frame_tmp, receita["titulo"])
    frame_tmp.unlink(missing_ok=True)
    print(f"         ✅ {video_path.name}")

    # 5. Upload YouTube
    video_id = ""
    youtube_habilitado = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if youtube_habilitado:
        print("\n📺 [5/5] Publicando no YouTube...")
        video_id = upload_youtube(
            video_path,
            receita["titulo"],
            receita["descricao_youtube"]
        )
    else:
        print("\n⚠️  [5/5] YOUTUBE_REFRESH_TOKEN não configurado — pulando upload")

    # Salva histórico + descrição
    salvar_historico(receita["titulo"])
    desc_path = video_path.with_suffix(".txt")
    desc_path.write_text(
        f"TÍTULO:\n{receita['titulo']}\n\n"
        f"YOUTUBE ID: {video_id}\n\n"
        f"DESCRIÇÃO YOUTUBE:\n{receita['descricao_youtube']}",
        encoding="utf-8"
    )

    print("\n" + "═"*54)
    print("  ✅ CONCLUÍDO!")
    print(f"  📁 {video_path.name}")
    if video_id:
        print(f"  🔗 https://youtube.com/shorts/{video_id}")
    print("═"*54 + "\n")

    return {"titulo": receita["titulo"], "video_id": video_id, "path": str(video_path)}


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for i in range(quantidade):
        if quantidade > 1:
            print(f"\n{'─'*54}\n  Vídeo {i+1} de {quantidade}")
        try:
            gerar_e_postar()
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            import traceback
            traceback.print_exc()