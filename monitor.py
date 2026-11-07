# monitor.py -> números de saúde da API, guardados na memória enquanto ela roda
# (o painel do Backend mostra: há quanto tempo está no ar, quantas requisições,
#  tempo médio de resposta). Zera quando o uvicorn reinicia.
import time

INICIO = time.time()
estatisticas = {"requisicoes": 0, "erros_500": 0, "tempo_total_ms": 0.0, "por_rota": {}}


def registrar(rota: str, ms: float, codigo: int):
    estatisticas["requisicoes"] += 1
    estatisticas["tempo_total_ms"] += ms
    if codigo >= 500:
        estatisticas["erros_500"] += 1
    item = estatisticas["por_rota"].setdefault(rota, {"chamadas": 0, "tempo_total_ms": 0.0})
    item["chamadas"] += 1
    item["tempo_total_ms"] += ms
