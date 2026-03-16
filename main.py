"""
╔══════════════════════════════════════════════════════╗
║        CULINÁRIA HORMONAL - Gerador Automático       ║
║  Gera receita → imagens → layout → vídeo completo   ║
║  + Upload automático para YouTube                    ║
║  VERSÃO 2.0 - Histórico Inteligente + Ganchos Virais ║
╚══════════════════════════════════════════════════════╝
"""

import os
import json
import random
import subprocess
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from difflib import SequenceMatcher

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

# Histórico: usa volume persistente na Railway (/data) ou pasta local no PC
_VOLUME_DIR  = Path("/data")
_HISTORY_DIR = _VOLUME_DIR if _VOLUME_DIR.exists() else BASE_DIR
HISTORY_FILE = _HISTORY_DIR / "historico_receitas_v2.json"

CANVAS_W = 1080
CANVAS_H = 1920

# ─── DESCRIÇÃO FIXA DO YOUTUBE ────────────────────────────────────────────────

DESCRICAO_YOUTUBE = (
    "Calor do nada, insônia, raiva sem motivo, choro escondido e ainda engorda mesmo "
    "comendo pouco... Você não tá ficando louca. Seu corpo só tá em colapso, e ninguém "
    "te explicou.\n\n"
    "Essa receita faz parte do Reset Hormonal, um plano de 7 dias 100% natural, feito "
    "pra quem tá cansada de fingir que tá tudo bem enquanto sofre sozinha.\n\n"
    "👉 PARA ACESSAR: Toque no nome do canal (no video mesmo) e depois no LINK que está "
    "no perfil. Faça esse favor para si mesma..."
)

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

from PIL import Image, ImageDraw, ImageFont
import io

# ─── HISTÓRICO ENRIQUECIDO ────────────────────────────────────────────────────

def carregar_historico() -> list:
    """Carrega histórico completo com detalhes das receitas."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data.get("receitas", [])
        except json.JSONDecodeError:
            print("⚠️  Arquivo de histórico corrompido. Criando novo...")
            return []
    return []

def salvar_historico(receita_completa: dict):
    """
    Salva receita no histórico com todos os detalhes.
    
    Estrutura:
    {
        "titulo": "...",
        "tipo_prato": "patê|mousse|salada|sopa|bebida|etc",
        "ingredientes_principais": ["ing1", "ing2", "ing3"],
        "beneficio_principal": "energia|sono|memoria|intestino|metabolismo|etc",
        "categoria": "cafe_manha|almoco|janta|lanche|sobremesa|bebida",
        "tempo_preparo": "5_minutos|10_minutos|15_minutos|30_minutos+",
        "data": "2026-03-16",
        "descricao_card": "...",
        "ingredientes_completos": "..."
    }
    """
    historico = carregar_historico()
    
    # Adiciona timestamp se não existir
    if "data" not in receita_completa:
        receita_completa["data"] = datetime.now().strftime("%Y-%m-%d")
    
    historico.append(receita_completa)
    
    # Mantém apenas últimas 200 receitas
    historico = historico[-200:]
    
    HISTORY_FILE.write_text(
        json.dumps({"receitas": historico}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"         📝 Histórico atualizado ({len(historico)} receitas salvas)")

def verificar_similaridade(nova_receita: dict, historico: list, limite_similaridade: float = 0.7) -> tuple:
    """
    Verifica se a nova receita é muito similar às existentes.
    Retorna (é_similar, motivo)
    """
    if not historico:
        return False, ""
    
    # Extrai ingredientes principais da nova receita (normalizados)
    novos_ingredientes = set(
        ing.lower().strip() 
        for ing in nova_receita.get("ingredientes_principais", [])
    )
    
    novo_tipo = nova_receita.get("tipo_prato", "").lower()
    novo_beneficio = nova_receita.get("beneficio_principal", "").lower()
    
    for receita_antiga in reversed(historico[-50:]):  # Verifica últimas 50
        antigos_ingredientes = set(
            ing.lower().strip() 
            for ing in receita_antiga.get("ingredientes_principais", [])
        )
        
        antigo_tipo = receita_antiga.get("tipo_prato", "").lower()
        antigo_beneficio = receita_antiga.get("beneficio_principal", "").lower()
        
        # Calcula similaridade de ingredientes (Jaccard)
        if novos_ingredientes and antigos_ingredientes:
            intersecao = len(novos_ingredientes & antigos_ingredientes)
            uniao = len(novos_ingredientes | antigos_ingredientes)
            similaridade_ingredientes = intersecao / uniao if uniao > 0 else 0
        else:
            similaridade_ingredientes = 0
        
        # Verifica se é o MESMO tipo de prato + ingredientes similares
        if novo_tipo == antigo_tipo and similaridade_ingredientes >= 0.6:
            return True, f"Tipo '{novo_tipo}' com ingredientes muito similares ({similaridade_ingredientes:.0%})"
        
        # Verifica se é a MESMA combinação exata de ingredientes principais
        if novos_ingredientes == antigos_ingredientes:
            return True, "Mesmos ingredientes principais"
        
        # Verifica se repetiu benefício + tipo muito recentemente (últimos 7 dias)
        try:
            data_antiga = datetime.strptime(receita_antiga.get("data", "2000-01-01"), "%Y-%m-%d")
            dias_desde = (datetime.now() - data_antiga).days
            
            if dias_desde < 7 and novo_beneficio == antigo_beneficio and novo_tipo == antigo_tipo:
                return True, f"Benefício '{novo_beneficio}' + tipo '{novo_tipo}' repetido há {dias_desde} dias"
        except:
            pass
    
    return False, ""

# ─── GERAÇÃO DE RECEITA ───────────────────────────────────────────────────────

def gerar_receita(historico: list) -> dict:
    """Gera receita usando Gemini com base nos padrões virais identificados."""
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Prepara histórico enriquecido para o prompt
    if historico:
        historico_str = "\n".join([
            f"{i+1}. {r.get('tipo_prato', 'PRATO').upper()} de {', '.join(r.get('ingredientes_principais', []))} → {r.get('beneficio_principal', 'benefício').upper()} ({r.get('data', 'N/A')})"
            for i, r in enumerate(historico[-30:])  # Últimas 30 receitas
        ])
        
        # Extrai ingredientes já usados recentemente (últimas 15 receitas)
        ingredientes_recentes = set()
        for r in historico[-15:]:
            ingredientes_recentes.update(ing.lower() for ing in r.get("ingredientes_principais", []))
        
        ingredientes_recentes_str = ", ".join(sorted(ingredientes_recentes)) if ingredientes_recentes else "Nenhum"
        
        # Conta frequência de benefícios
        beneficios_count = {}
        for r in historico[-30:]:
            benef = r.get("beneficio_principal", "outro")
            beneficios_count[benef] = beneficios_count.get(benef, 0) + 1
        
        beneficios_mais_usados = sorted(beneficios_count.items(), key=lambda x: x[1], reverse=True)[:5]
        beneficios_str = ", ".join(f"{b} ({c}x)" for b, c in beneficios_mais_usados)
    else:
        historico_str = "Nenhuma receita publicada ainda."
        ingredientes_recentes_str = "Nenhum"
        beneficios_str = "Nenhum"

    prompt = f"""Você é especialista em criação de conteúdo viral para o canal "Culinária Hormonal" no YouTube.

📊 CONTEXTO DO CANAL:
- Público: Mulheres 40+ sofrendo com sintomas hormonais (menopausa, TPM, desregulação)
- Dores principais: ganho de peso, inchaço, insônia, fadiga, fogachos, memória fraca, humor instável
- Produto: "Reset Hormonal em 7 Dias" (infoproduto vendido na descrição)

🎯 PADRÕES DE TÍTULOS VIRAIS (USE ESTES GANCHOS):

TIPO 1 - "Esse [prato] + benefício forte + tempo":
  • "Esse patê salvou minha memória (Pronto em 2 minutos!)"
  • "Esse mousse te faz dormir como um anjo (É só tem 3 ingredientes!)"

TIPO 2 - "O [familiar] que NÃO é [óbvio]":
  • "O 'leite condensado' que não tem leite nem açúcar"
  • "O 'mingau' que não é mingau e me deixou sem fome"

TIPO 3 - "Meu/Minha [refeição] + hack inteligente":
  • "Meu café da manhã energético pronto enquanto eu durmo"
  • "Minha vitamina 'Apaga-Fogo' que me salvou dos calorões"

TIPO 4 - "[Prato] que + verbo de ação forte":
  • "Os ovos mexidos que espantam o cansaço da manhã"
  • "A sopa que organizou meu intestino de vez"

TIPO 5 - "Poucos sabem o poder desse...":
  • "Poucos sabem o poder desse patê"
  • "O segredo que poucas conhecem para..."

REGRAS DOS TÍTULOS:
✓ Máximo 65 caracteres (ideal: 40-55)
✓ Use gatilhos: poder, segredo, espanta, salva, cura, diferente, poucos sabem
✓ Seja específico no benefício (não diga "saúde", diga "memória", "sono", "energia")
✓ Quando possível, mencione tempo ou número de ingredientes
✓ NUNCA use títulos genéricos como "Receita saudável" ou "Delícia nutritiva"

═══════════════════════════════════════════════════════════════

📚 HISTÓRICO DE RECEITAS PUBLICADAS (NÃO REPITA):

{historico_str}

🚫 INGREDIENTES USADOS RECENTEMENTE (evite repetir os mesmos):
{ingredientes_recentes_str}

📈 BENEFÍCIOS MAIS EXPLORADOS (priorize outros):
{beneficios_str}

═══════════════════════════════════════════════════════════════

🥘 CATEGORIAS PARA ALTERNAR (escolha uma diferente das últimas):
- Patês/Pastes (sardinha, grão-de-bico, feijão, beterraba)
- Mousses/Doces (abacate, batata-doce, chia)
- Bebidas/Vitaminas (leites vegetais, smoothies)
- Café da manhã overnight (aveia, chia, iogurte)
- Ovos (mexidos, cozidos, omeletes)
- Saladas (repolho, beterraba, quinoa, folhas)
- Sopas (couve-flor, abóbora, erva-doce, legumes)
- Snacks rápidos (grãos assados, bolachas)
- Pratos principais (frango, peixe, carne)

═══════════════════════════════════════════════════════════════

📝 ESTRUTURA DA DESCRIÇÃO DO CARD (aparece no vídeo):

FRASE 1 - CONEXÃO COM A DOR (pergunta ou afirmação):
  • "Cérebro lento, esquecendo o que ia falar?"
  • "Mente agitada, corpo cansado?"
  • "Acordando com aquele calorão noturno?"
  • "Intestino bagunçado?"
  • "Vontade de mastigar algo salgado e crocante?"

FRASES 2-3 - MODO DE PREPARO SIMPLES (seja específico):
  • "Amasse meia lata de sardinha em óleo..."
  • "Misture 4 colheres de sopa de aveia em flocos..."
  • "Bata 1 abacate maduro, 2 colheres de cacau..."
  • Use quantidades exatas e ingredientes reais

FRASE 4 - BENEFÍCIO NATURAL (conecte com hormônios):
  • "Vira uma calda cremosa que engana até doceiro"
  • "Energia que dura a manhã inteira"
  • "Relaxa o corpo todo em 30 minutos"
  • "Enche de fibras para comer com palitos"

FRASE 5 - CTA FINAL (obrigatório):
  "(Leia mais na descrição)" ou "(LEIA A DESCRIÇÃO)"

REGRAS DA DESCRIÇÃO:
✓ 4-6 frases curtas (máximo 15 palavras cada), não quebre linha entre as frases, deixe o texto corrido
✓ Linguagem de "dica de amiga" - informal, acolhedora
✓ NUNCA use jargões técnicos ou termos científicos
✓ Seja específica nos ingredientes e quantidades
✓ Termine SEMPRE com "(LEIA A DESCRIÇÃO)"

═══════════════════════════════════════════════════════════════

 PROMPTS DE IMAGEM (para IA gerar fotos):

PROMPT 1 - INGREDIENTES (mise en place):
  • Descreva TODOS os ingredientes com quantidades exatas
  • Mencione disposição artística na mesa/bancada
  • Estilo: fotorrealista, iluminação natural, food photography
  • Exemplo: "Top view of 1 can sardines in oil, 2 tablespoons natural yogurt, 1 tablespoon chopped walnuts, fresh lemon, sea salt, black pepper, arranged on rustic wooden board"

PROMPT 2 - PRATO PRONTO (hero shot):
  • Mostre o prato finalizado, apetitoso, dando água na boca
  • Adicione: "vibrant colors, appetizing, steam rising, mouth-watering hero shot, professional food photography"
  • Seja específico na apresentação (em cima de torrada? em taça? em prato?)

═══════════════════════════════════════════════════════════════

🎯 SUA TAREFA AGORA:

Crie UMA receita NOVA seguindo TODAS as regras acima.

IMPORTANTE:
1. Escolha um tipo de prato DIFERENTE das últimas 5 receitas
2. Use ingredientes NÃO repetidos recentemente
3. Priorize benefícios MENOS explorados no histórico
4. Siga EXATAMENTE os padrões de títulos virais mostrados
5. Seja específica na descrição (quantidades, tempos, ingredientes)

Responda SOMENTE em JSON válido, sem markdown, sem texto extra:
{{
  "titulo": "Título viral seguindo os padrões (máx 65 caracteres)",
  "descricao_card": "Descrição completa em 4-6 frases terminando com (Leia mais na descrição)",
  "tipo_prato": "patê|mousse|salada|sopa|bebida|cafe_manha|ovos|snack|prato_principal|doce",
  "ingredientes_principais": ["ingrediente1", "ingrediente2", "ingrediente3"],
  "beneficio_principal": "energia|sono|memoria|intestino|metabolismo|foco|ansiedade|inchaço|caloroes|imunidade",
  "categoria": "cafe_manha|almoco|janta|lanche|sobremesa|bebida",
  "tempo_preparo": "5_minutos|10_minutos|15_minutos|30_minutos+",
  "prompt_ingredientes": "Prompt em inglês descrevendo mise en place com quantidades",
  "prompt_prato_pronto": "Prompt em inglês do prato finalizado hero shot"
}}"""

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    
    # Limpa markdown se existir
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        receita = json.loads(text)
        
        # Valida campos obrigatórios
        campos_obrigatorios = ["titulo", "descricao_card", "tipo_prato", 
                             "ingredientes_principais", "beneficio_principal",
                             "prompt_ingredientes", "prompt_prato_pronto"]
        
        for campo in campos_obrigatorios:
            if campo not in receita:
                raise ValueError(f"Campo obrigatório ausente: {campo}")
        
        # Adiciona campos opcionais com defaults
        receita.setdefault("categoria", "lanche")
        receita.setdefault("tempo_preparo", "10_minutos")
        
        return receita
        
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear JSON da Gemini: {e}")
        print(f"Resposta recebida: {text[:200]}...")
        raise

# ─── GERAÇÃO DE IMAGENS ───────────────────────────────────────────────────────

def gerar_imagens(prompt_ingredientes: str, prompt_prato: str):
    """Gera imagens usando Imagen via Gemini API."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)

    prefixo = "Professional food photography, cinematic lighting, ultra-realistic, beautiful composition, 8k quality: "
    sufixo_hero = ", vibrant colors, appetizing, steam rising, mouth-watering hero shot, garnished beautifully"

    def gerar(prompt: str, extra: str = "") -> Image.Image:
        # Configuração compatível com Imagen 4.0
        # NOTA: safety_filter_level só aceita "BLOCK_LOW_AND_ABOVE" neste modelo
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="BLOCK_LOW_AND_ABOVE",  # ← CORREÇÃO: valor suportado
            # person_generation removido: não é suportado no Imagen 4.0 fast
        )
        
        resultado = client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prefixo + prompt + extra,
            config=config
        )
        img_bytes = resultado.generated_images[0].image.image_bytes
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    print("  🖼️  Gerando imagem 1 (ingredientes)...")
    try:
        img1 = gerar(prompt_ingredientes)
    except Exception as e:
        print(f"  ⚠️  Erro na imagem 1: {e}")
        print("  🔄 Tentando com prompt simplificado...")
        # Fallback: prompt mais genérico
        img1 = gerar("fresh ingredients on wooden table, natural lighting, food photography")
    
    print("  🖼️  Gerando imagem 2 (prato pronto)...")
    try:
        img2 = gerar(prompt_prato, sufixo_hero)
    except Exception as e:
        print(f"  ⚠️  Erro na imagem 2: {e}")
        print("  🔄 Tentando com prompt simplificado...")
        img2 = gerar("delicious finished dish, professional food photography, appetizing")

    return img1, img2

# ─── MONTAGEM DO LAYOUT ───────────────────────────────────────────────────────

def arredondar_cantos(img: Image.Image, radius: int) -> Image.Image:
    """Aplica cantos arredondados em uma imagem."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    result = img.copy().convert("RGBA")
    result.putalpha(mask)
    return result

def quebrar_texto(draw: ImageDraw.Draw, texto: str, fonte, max_w: int) -> list:
    """Quebra texto em múltiplas linhas respeitando largura máxima."""
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
    """Monta o layout final do vídeo no formato vertical (1080x1920)."""
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def carregar_fonte_win(bold: bool, tamanho: int):
        """Carrega fonte tentando múltiplos caminhos (Windows/Linux)."""
        if bold:
            nomes = ["arialbd.ttf", "Arial_Bold.ttf", "arial_bold.ttf"]
            fallbacks = ["DejaVuSans-Bold.ttf"]
        else:
            nomes = ["arial.ttf", "Arial.ttf"]
            fallbacks = ["DejaVuSans.ttf"]
        
        for nome in nomes + fallbacks:
            caminhos = [
                Path(f"C:/Windows/Fonts/{nome}"),
                ASSETS_DIR / "fonts" / nome,
                Path(f"/usr/share/fonts/truetype/dejavu/{nome}"),
                Path(f"/usr/share/fonts/TTF/{nome}"),
            ]
            for c in caminhos:
                if c.exists():
                    return ImageFont.truetype(str(c), tamanho)
        
        # Fallback final
        print(f"⚠️  Fonte não encontrada, usando default")
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

    # Título
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

    # Imagens
    img_w = IMGS_W // 2
    img_h = IMGS_H

    img1_rs = img_ingredientes.resize((img_w, img_h), Image.LANCZOS)
    img2_rs = img_prato.resize((img_w, img_h), Image.LANCZOS)
    img1_rd = arredondar_cantos(img1_rs, CORNER_R)
    img2_rd = arredondar_cantos(img2_rs, CORNER_R)

    canvas.paste(img1_rd, (0, IMGS_Y), img1_rd)
    canvas.paste(img2_rd, (img_w, IMGS_Y), img2_rd)

    # Descrição
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

    # Logo
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
    """Verifica se FFmpeg está instalado."""
    import shutil
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg não encontrado!\n"
            "Instale em: https://www.gyan.dev/ffmpeg/builds/  \n"
            "Baixe 'ffmpeg-release-essentials.zip', extraia e adicione a pasta bin ao PATH."
        )

def montar_video(frame_png: Path, titulo: str) -> Path:
    """
    Combina vídeo de fundo (loop 6s) + frame PNG + trecho ALEATÓRIO de 6s do áudio → .mp4
    """
    verificar_ffmpeg()

    DURACAO = 5  # Duração do vídeo em segundos

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

    # Gera nome do arquivo seguro
    nome = (titulo[:40].replace(" ", "_")
                       .replace("/", "-")
                       .replace("'", "")
                       .replace("(", "")
                       .replace(")", "")
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
    Faz upload do vídeo para o YouTube como Short (público por padrão).
    Retorna o ID do vídeo publicado.
    """
    import google.oauth2.credentials
    import googleapiclient.discovery
    import googleapiclient.http

    # Credenciais OAuth2 via variáveis de ambiente (Railway)
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",  # CORREÇÃO: removido espaço
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
    print("  🌿 CULINÁRIA HORMONAL — Gerador Automático v2.0")
    print("═"*54)

    for pasta in [OUTPUT_DIR, ASSETS_DIR, BG_VIDEOS_DIR, MUSIC_DIR]:
        pasta.mkdir(parents=True, exist_ok=True)

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY não encontrada. Configure o arquivo .env")

    # 1. Receita (com retry em caso de similaridade)
    print("\n📝 [1/5] Gerando receita...")
    historico = carregar_historico()
    print(f"         Histórico: {len(historico)} receitas já publicadas")
    
    max_tentativas = 3
    receita = None
    
    for tentativa in range(max_tentativas):
        try:
            receita = gerar_receita(historico)
            print(f"         ✅ {receita['titulo']}")
            
            # Verifica similaridade
            e_similar, motivo = verificar_similaridade(receita, historico)
            if e_similar and tentativa < max_tentativas - 1:
                print(f"         ⚠️  Receita similar: {motivo}")
                print(f"         🔄 Tentando gerar outra... ({tentativa + 2}/{max_tentativas})")
                continue
            
            # Extrai ingredientes completos da descrição para salvar
            receita["ingredientes_completos"] = receita.get("descricao_card", "")
            
            break
            
        except Exception as e:
            if tentativa == max_tentativas - 1:
                raise
            print(f"         ⚠️  Erro na tentativa {tentativa + 1}: {e}")
            continue
    
    if not receita:
        raise RuntimeError("Não foi possível gerar uma receita única após múltiplas tentativas")

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
        try:
            video_id = upload_youtube(
                video_path,
                receita["titulo"],
                DESCRICAO_YOUTUBE
            )
        except Exception as e:
            print(f"\n⚠️  Erro no upload: {e}")
            print("         Vídeo salvo localmente, tente upload manual")
    else:
        print("\n⚠️  [5/5] YOUTUBE_REFRESH_TOKEN não configurado — pulando upload")

    # Salva histórico enriquecido
    salvar_historico(receita)
    
    # Salva descrição completa em arquivo
    desc_path = video_path.with_suffix(".txt")
    desc_path.write_text(
        f"TÍTULO:\n{receita['titulo']}\n\n"
        f"TIPO: {receita.get('tipo_prato', 'N/A').upper()}\n"
        f"BENEFÍCIO: {receita.get('beneficio_principal', 'N/A').upper()}\n"
        f"INGREDIENTES: {', '.join(receita.get('ingredientes_principais', []))}\n\n"
        f"YOUTUBE ID: {video_id}\n"
        f"URL: https://youtube.com/shorts/{video_id}\n\n"
        f"DESCRIÇÃO YOUTUBE:\n{DESCRICAO_YOUTUBE}\n\n"
        f"DESCRIÇÃO DO CARD:\n{receita['descricao_card']}",
        encoding="utf-8"
    )

    print("\n" + "═"*54)
    print("  ✅ CONCLUÍDO!")
    print(f"  📁 {video_path.name}")
    print(f"  🍽️  Tipo: {receita.get('tipo_prato', 'N/A')}")
    print(f"  💪 Benefício: {receita.get('beneficio_principal', 'N/A')}")
    print(f"  🥘 Ingredientes: {', '.join(receita.get('ingredientes_principais', []))}")
    if video_id:
        print(f"  🔗 https://youtube.com/shorts/{video_id}")
    print("═"*54 + "\n")

    return {
        "titulo": receita["titulo"],
        "video_id": video_id,
        "path": str(video_path),
        "tipo_prato": receita.get("tipo_prato"),
        "beneficio": receita.get("beneficio_principal"),
        "ingredientes": receita.get("ingredientes_principais", [])
    }


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    resultados = []
    
    print(f"\n🎯 Gerando {quantidade} vídeo(s)...")
    
    for i in range(quantidade):
        if quantidade > 1:
            print(f"\n{'─'*54}\n  🎬 Vídeo {i+1} de {quantidade}")
        try:
            resultado = gerar_e_postar()
            resultados.append(resultado)
            
            # Aguarda entre vídeos para não sobrecarregar APIs
            if i < quantidade - 1 and quantidade > 1:
                print(f"⏳ Aguardando 30 segundos antes do próximo...")
                import time
                time.sleep(30)
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            
            # Continua para o próximo vídeo mesmo com erro
            if i < quantidade - 1:
                continuar = input("Continuar para o próximo vídeo? (s/n): ")
                if continuar.lower() != 's':
                    break
    
    # Resumo final
    if quantidade > 1 and resultados:
        print("\n" + "═"*54)
        print("  📊 RESUMO DA GERAÇÃO")
        print("═"*54)
        for i, r in enumerate(resultados, 1):
            print(f"  {i}. {r['titulo']}")
            print(f"     🍽️ {r.get('tipo_prato', 'N/A')} | 💪 {r.get('beneficio', 'N/A')}")
        print("═"*54 + "\n")