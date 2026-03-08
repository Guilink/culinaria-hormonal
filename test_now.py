"""
Teste imediato — roda o pipeline completo UMA VEZ agora.
Use para validar que tudo funciona na Railway antes de esperar o scheduler.

Na Railway: mude o CMD do Dockerfile para rodar esse arquivo,
deploy, veja os logs, depois volte o CMD para scheduler.py
"""

from main import gerar_e_postar, load_env

load_env()

print("🧪 MODO TESTE — Rodando pipeline completo agora...")
print("=" * 54)

try:
    resultado = gerar_e_postar()
    print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
    print(f"   Título  : {resultado['titulo']}")
    if resultado.get("video_id"):
        print(f"   YouTube : https://youtube.com/shorts/{resultado['video_id']}")
except Exception as e:
    print(f"\n❌ ERRO NO TESTE: {e}")
    import traceback
    traceback.print_exc()