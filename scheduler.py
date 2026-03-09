"""
╔══════════════════════════════════════════════════════╗
║     CULINÁRIA HORMONAL — Agendador Diário            ║
║  Roda 24/7 na Railway e posta 5 vídeos/dia           ║
╚══════════════════════════════════════════════════════╝

Horários (Brasília / America/Sao_Paulo):
  Vídeo 1: 10:00 – 10:30  (aleatório dentro da janela)
  Vídeo 2: 12:00 – 12:30
  Vídeo 3: 14:00 – 14:30
  Vídeo 4: 16:30 – 17:00
  Vídeo 5: 19:00 – 19:30
"""

import time
import random
import logging
from datetime import datetime, timedelta
import pytz

# Importa o pipeline principal
from main import gerar_e_postar, load_env

# ─── CONFIGURAÇÕES ────────────────────────────────────────────────────────────

load_env()

TZ = pytz.timezone("America/Sao_Paulo")

# Janelas de publicação: (hora_inicio, minuto_inicio, hora_fim, minuto_fim)
# Janelas sugeridas para Nicho de Saúde/Culinária Hormonal
# Foco: Momentos de decisão alimentar (Refeições e Planejamento)

JANELAS = [
    (7, 30, 8, 00),   # Vídeo 1: Despertar/Shot/Café (Início do metabolismo)
    (11, 00, 11, 30),   # Vídeo 2: Almoço/Planejamento (Antes da fome bater)
    (14, 30, 15, 00),   # Vídeo 3: Lanche da tarde/Controle de ansiedade/Doce saudável
    (18, 00, 18, 30),   # Vídeo 4: Jantar/O "Horário de Ouro" do YouTube
    (21, 00, 21, 30),   # Vídeo 5: Ceia/Chás/Higiene do sono (Foco hormonal noturno)
]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("scheduler")

# ─── LÓGICA DO AGENDADOR ──────────────────────────────────────────────────────

def calcular_horarios_do_dia(data: datetime) -> list[datetime]:
    """
    Para cada janela, sorteia um horário aleatório dentro dela
    e retorna lista ordenada de datetimes com timezone.
    """
    # Garante que 'data' está em Brasília antes de fazer o replace
    data_br = data.astimezone(TZ)
    horarios = []
    for h_ini, m_ini, h_fim, m_fim in JANELAS:
        inicio = data_br.replace(hour=h_ini, minute=m_ini, second=0, microsecond=0)
        fim    = data_br.replace(hour=h_fim, minute=m_fim, second=0, microsecond=0)
        # Sorteia segundo aleatório dentro da janela
        delta_segundos = int((fim - inicio).total_seconds())
        offset = random.randint(0, delta_segundos)
        horario = inicio + timedelta(seconds=offset)
        horarios.append(horario)
    return sorted(horarios)


def aguardar_ate(horario: datetime):
    """Dorme até o horário alvo, logando de minuto em minuto."""
    agora = datetime.now(TZ)
    espera = (horario - agora).total_seconds()
    if espera <= 0:
        return
    log.info(f"⏳ Próximo vídeo às {horario.strftime('%H:%M:%S')} "
             f"(aguardando {int(espera//60)}min {int(espera%60)}s)")
    while True:
        agora = datetime.now(TZ)
        restante = (horario - agora).total_seconds()
        if restante <= 0:
            break
        # Log a cada minuto
        if int(restante) % 60 == 0:
            log.info(f"  ⏱  {int(restante//60)} min restantes...")
        time.sleep(min(30, restante))


def rodar_loop():
    """Loop principal: calcula horários do dia e executa cada vídeo no momento certo."""
    log.info("🚀 Scheduler iniciado — Culinária Hormonal")
    log.info(f"   Timezone: {TZ}")
    log.info(f"   Janelas configuradas: {len(JANELAS)} vídeos/dia")

    while True:
        agora = datetime.now(TZ)
        horarios_hoje = calcular_horarios_do_dia(agora)

        log.info(f"\n📅 Horários de hoje ({agora.strftime('%d/%m/%Y')}):")
        for i, h in enumerate(horarios_hoje, 1):
            log.info(f"   Vídeo {i}: {h.strftime('%H:%M:%S')}")

        videos_feitos_hoje = 0

        for i, horario in enumerate(horarios_hoje, 1):
            agora = datetime.now(TZ)

            # Pula horários que já passaram (ex: scheduler iniciou no meio do dia)
            if horario < agora:
                log.info(f"⏭️  Vídeo {i} ({horario.strftime('%H:%M')}) já passou — pulando")
                continue

            # Aguarda o momento certo
            aguardar_ate(horario)

            log.info(f"\n{'='*50}")
            log.info(f"🎬 INICIANDO VÍDEO {i}/5 — {datetime.now(TZ).strftime('%H:%M:%S')}")
            log.info(f"{'='*50}")

            try:
                resultado = gerar_e_postar()
                videos_feitos_hoje += 1
                log.info(f"✅ Vídeo {i} publicado: {resultado['titulo']}")
                if resultado.get("video_id"):
                    log.info(f"   🔗 https://youtube.com/shorts/{resultado['video_id']}")
            except Exception as e:
                log.error(f"❌ Erro no vídeo {i}: {e}", exc_info=True)

        log.info(f"\n🏁 Dia concluído: {videos_feitos_hoje}/{len(JANELAS)} vídeos publicados")

        # Calcula quanto tempo falta para meia-noite do próximo dia
        amanha = (datetime.now(TZ) + timedelta(days=1)).replace(
            hour=0, minute=1, second=0, microsecond=0
        )
        espera_noite = (amanha - datetime.now(TZ)).total_seconds()
        log.info(f"😴 Dormindo até meia-noite ({int(espera_noite//3600)}h "
                 f"{int((espera_noite%3600)//60)}min)...")
        time.sleep(max(60, espera_noite))


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rodar_loop()
