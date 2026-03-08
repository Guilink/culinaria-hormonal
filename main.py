"""
╔══════════════════════════════════════════════════════╗
║        CULINÁRIA HORMONAL - Gerador Automático       ║
║  Gera receita → imagens → layout → vídeo completo   ║
╚══════════════════════════════════════════════════════╝

Dependências (instale antes de rodar):
    pip install pillow moviepy google-generativeai requests

APIs necessárias (configure no arquivo .env):
    GEMINI_API_KEY=AIza...   ← UMA SÓ CHAVE para tudo!

Custo estimado:
    Texto  (Gemini 2.0 Flash): GRÁTIS no free tier
    Imagens (Imagen 3 Fast):   ~$0.015/imagem → $0.03/vídeo
    5 vídeos/dia × 30 dias  =  ~$4.50/mês 💚
"""

import os
import json
import random
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

# Modelo de imagem:
#   "imagen-3.0-fast-generate-001" → mais barato (~$0.015/img) ✅ recomendado
#   "imagen-3.0-generate-002"      → máxima qualidade (~$0.030/img)
IMAGEN_MODEL = "imagen-4.0-fast-generate-001"

# Pastas do projeto
BASE_DIR      = Path(__file__).parent
ASSETS_DIR    = BASE_DIR / "assets"       # coloque logo.png aqui
BG_VIDEOS_DIR = BASE_DIR / "bg_videos"   # vídeos de fundo .mp4
MUSIC_DIR     = BASE_DIR / "music"       # músicas .mp3 / .m4a
OUTPUT_DIR    = BASE_DIR / "output"
HISTORY_FILE  = BASE_DIR / "historico_receitas.json"

# Canvas formato vertical (Shorts)
CANVAS_W = 1080
CANVAS_H = 1920

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

from PIL import Image, ImageDraw, ImageFont
import io

# ─── HISTÓRICO ────────────────────────────────────────────────────────────────

def carregar_historico() -> list:
    """Carrega títulos já publicados para evitar repetição."""
    if HISTORY_FILE.exists():
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data.get("titulos", [])
    return []

def salvar_historico(titulo: str):
    """Adiciona título ao histórico (mantém últimos 200)."""
    historico = carregar_historico()
    historico.append(titulo)
    historico = historico[-200:]
    HISTORY_FILE.write_text(
        json.dumps({"titulos": historico}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ─── GERAÇÃO DE RECEITA (GEMINI 2.0 FLASH - GRÁTIS) ──────────────────────────

def gerar_receita(historico: list) -> dict:
    """
    Usa Gemini 2.0 Flash para gerar receita nova no estilo do canal.
    Retorna dict com: titulo, descricao_card, descricao_youtube,
                      prompt_ingredientes, prompt_prato_pronto
    """
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

- Exemplos reais do canal (referência de estilo):

  "Poucos sabem o poder desse patê"
  "Leite condensado (sem leite)"
  "Café da manhã diferente"
  "O mousse que faz pegar no sono"
  "Para espantar o cansaço"
  "Esse molho revolucionou minha salada"
  "Troquei o pão por isso e minha energia melhorou"
  "O peixe com tomate cereja que se faz sozinho no forno"

- NÃO usar títulos longos ou explicativos demais
- Priorizar curiosidade + benefício


═══ REGRAS DA DESCRIÇÃO DO CARD (aparece no vídeo) ═══

- 4–5 frases curtas
- Primeira frase: conectar com um problema comum
  (cansaço, sono ruim, fome fora de hora, falta de energia)
- Segunda e terceira frases: Explicar a receita de forma simples e rápida, passe os ingredientes e o modo de preparo corretamente de maneira sucinta.
- Quarta frase: mencionar benefícios naturais do alimento, exemplo: (energia, saciedade, relaxamento, foco, digestão)
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

# ─── GERAÇÃO DE IMAGENS (IMAGEN 3 FAST - ~$0.015/img) ────────────────────────

def gerar_imagens(prompt_ingredientes: str, prompt_prato: str):
    """
    Gera as 2 imagens usando Imagen 3 Fast via Gemini API.
    Mesma chave do texto — sem OpenAI.
    """
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

# ─── MONTAGEM DO LAYOUT (PILLOW) ──────────────────────────────────────────────

def arredondar_cantos(img: Image.Image, radius: int) -> Image.Image:
    """Aplica cantos arredondados com máscara alpha."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    result = img.copy().convert("RGBA")
    result.putalpha(mask)
    return result

def quebrar_texto(draw: ImageDraw.Draw, texto: str, fonte, max_w: int) -> list:
    """Quebra texto em linhas respeitando largura máxima."""
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
    """
    Monta frame 1080x1920:
      - Título com fundo BRANCO logo acima das imagens
      - 2 imagens lado a lado com cantos arredondados
      - Logo redondo centralizado na BORDA INFERIOR das imagens
      - Caixa branca com descrição embaixo
    """
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # ── Fontes com suporte a acentos (Arial do Windows) ───────────────────
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

    # ── Medidas exatas ────────────────────────────────────────────────────
    TITULO_Y     = 180                  # 180px do topo
    titulo_max_w = CANVAS_W - 110 * 2  # margem 110px cada lado
    titulo_lh    = int(52 * 1.18)

    IMGS_Y = 380                        # imagens a 380px do topo
    IMGS_W = CANVAS_W                   # largura total 1080px
    IMGS_H = IMGS_W // 2               # quadrado

    LOGO_Y = 800                        # logo a 800px do topo
    logo_size = 115

    DESC_X = 40                         # 40px da esquerda
    DESC_W = 830                        # largura máxima 830px
    DESC_Y = IMGS_Y + IMGS_H + 20      # 20px abaixo das imagens

    linhas_titulo = quebrar_texto(draw, receita["titulo"].upper(), fonte_titulo, titulo_max_w)

    # ── Título com fundo BRANCO negrito ──────────────────────────────────
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

    # ── Imagens lado a lado — largura total 1080px ────────────────────────
    img_w = IMGS_W // 2
    img_h = IMGS_H

    img1_rs = img_ingredientes.resize((img_w, img_h), Image.LANCZOS)
    img2_rs = img_prato.resize((img_w, img_h), Image.LANCZOS)
    img1_rd = arredondar_cantos(img1_rs, CORNER_R)
    img2_rd = arredondar_cantos(img2_rs, CORNER_R)

    canvas.paste(img1_rd, (0, IMGS_Y), img1_rd)
    canvas.paste(img2_rd, (img_w, IMGS_Y), img2_rd)

    # ── Caixa branca com descrição ────────────────────────────────────────
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

    # ── Logo redondo a 800px do topo — desenhado POR ÚLTIMO (frente de tudo) ──
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


# ─── MONTAGEM DO VÍDEO (FFMPEG) ───────────────────────────────────────────────

def verificar_ffmpeg():
    """Verifica se FFmpeg está instalado."""
    import shutil
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg não encontrado!\n"
            "Instale em: https://www.gyan.dev/ffmpeg/builds/\n"
            "Baixe 'ffmpeg-release-essentials.zip', extraia e adicione a pasta bin ao PATH."
        )

def montar_video(frame_png: Path, titulo: str) -> Path:
    """Combina vídeo de fundo (loop 6s) + frame PNG + música → .mp4 via FFmpeg."""
    import subprocess

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
    print(f"  🎬 Fundo  : {bg_path.name}")
    print(f"  🎵 Música : {musica_path.name}")

    nome = (titulo[:40].replace(" ", "_")
                       .replace("/", "-")
                       .replace("'", "")
            + "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4")
    saida = OUTPUT_DIR / nome

    # Monta o comando FFmpeg:
    # - Loop no vídeo de fundo até 6s
    # - Sobrepõe o frame PNG em cima (ocupa todo o canvas)
    # - Adiciona música com volume 40% e fade out no último segundo
    # - Escala tudo para 1080x1920
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(bg_path),       # vídeo de fundo em loop
        "-loop", "1", "-i", str(frame_png),              # frame PNG estático
        "-stream_loop", "-1", "-i", str(musica_path),    # música em loop
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

# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def gerar_video_completo() -> Path:
    """Pipeline completo: receita → imagens → layout → vídeo."""

    print("\n" + "═"*54)
    print("  🌿 CULINÁRIA HORMONAL — Gerador Automático")
    print("═"*54)

    for pasta in [OUTPUT_DIR, ASSETS_DIR, BG_VIDEOS_DIR, MUSIC_DIR]:
        pasta.mkdir(parents=True, exist_ok=True)

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY não encontrada. Configure o arquivo .env")

    # 1. Receita
    print("\n📝 [1/4] Gerando receita (Gemini Flash — grátis)...")
    historico = carregar_historico()
    print(f"         Histórico: {len(historico)} receitas já publicadas")
    receita = gerar_receita(historico)
    print(f"         ✅ {receita['titulo']}")

    # 2. Imagens
    print("\n🖼️  [2/4] Gerando imagens (Imagen 3 Fast — ~$0.03)...")
    img_ingredientes, img_prato = gerar_imagens(
        receita["prompt_ingredientes"],
        receita["prompt_prato_pronto"]
    )
    print("         ✅ Imagens geradas")

    # 3. Layout
    print("\n🎨 [3/4] Montando layout...")
    frame = montar_layout(receita, img_ingredientes, img_prato)
    frame_tmp = OUTPUT_DIR / "_frame_temp.png"
    frame.save(str(frame_tmp), "PNG")
    print("         ✅ Layout pronto")

    # 4. Vídeo
    print("\n🎬 [4/4] Montando vídeo final...")
    video_path = montar_video(frame_tmp, receita["titulo"])
    frame_tmp.unlink(missing_ok=True)
    print(f"         ✅ {video_path.name}")

    # Salva histórico + descrição YouTube
    salvar_historico(receita["titulo"])
    desc_path = video_path.with_suffix(".txt")
    desc_path.write_text(
        f"TÍTULO:\n{receita['titulo']}\n\n"
        f"DESCRIÇÃO YOUTUBE:\n{receita['descricao_youtube']}",
        encoding="utf-8"
    )

    print("\n" + "═"*54)
    print("  ✅ CONCLUÍDO!")
    print(f"  📁 output/{video_path.name}")
    print(f"  📄 output/{desc_path.name}")
    print("═"*54 + "\n")
    return video_path

# ─── MODO LOTE ────────────────────────────────────────────────────────────────

def gerar_lote(quantidade: int):
    """Gera N vídeos em sequência."""
    print(f"\n🚀 Modo lote: {quantidade} vídeos")
    gerados = []
    for i in range(quantidade):
        print(f"\n{'─'*54}\n  Vídeo {i+1} de {quantidade}")
        try:
            gerados.append(gerar_video_completo())
        except Exception as e:
            print(f"  ❌ Erro: {e}")
    print(f"\n🏁 Concluído: {len(gerados)}/{quantidade} vídeos gerados\n")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if quantidade == 1:
        gerar_video_completo()
    else:
        gerar_lote(quantidade)