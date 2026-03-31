from datetime import datetime, timedelta
from collections import Counter


MOCK_USUARIOS = [
    {"id": 1, "nome": "Admin", "email": "admin@empresa.com", "nome_usuario": "admin", "role": "admin", "ativo": True},
    {"id": 2, "nome": "Gestor", "email": "gestora@empresa.com", "nome_usuario": "gestora", "role": "gestor", "ativo": True},
    {"id": 3, "nome": "Colaborador", "email": "user@empresa.com", "nome_usuario": "user", "role": "usuario", "ativo": True},
]

MOCK_LOCAIS = [
    {"id": 10, "codigo": "MATRIZ", "nome": "Matriz", "tipo": "Site", "pai_id": None},
    {"id": 11, "codigo": "BL01", "nome": "Bloco 01", "tipo": "Prédio", "pai_id": 10},
    {"id": 12, "codigo": "TI-01", "nome": "Sala TI", "tipo": "Sala", "pai_id": 11},
]

MOCK_ATIVOS = [
    {"id": 100, "patrimonio": "PAT-0001", "numero_serie": "SN-A1", "modelo": "Dell OptiPlex 7080", "categoria": "Desktop",
     "estado": "em_uso", "local_id": 12, "custodiante": "Colaborador"},
    {"id": 101, "patrimonio": "PAT-0002", "numero_serie": "SN-A2", "modelo": "Lenovo T14", "categoria": "Notebook",
     "estado": "estoque", "local_id": 12, "custodiante": ""},
]

MOCK_ITENS_ESTOQUE = [
    {"id": 200, "sku": "CAB-RJ45", "nome": "Cabo de Rede RJ45 2m", "unidade": "pc", "nivel_minimo": 10, "qtde": 25},
    {"id": 201, "sku": "MOUSE-USB", "nome": "Mouse USB", "unidade": "pc", "nivel_minimo": 5, "qtde": 3},
]

NOW = datetime.now()
MOCK_CHAMADOS = [
    {"id": 9001, "assunto": "Instabilidade no Wi-Fi", "descricao": "Quedas frequentes", "origem": "Infra",
     "prioridade": "alta", "status": "aberto", "aberto_em": NOW - timedelta(days=2), "ativo_id": None,
     "historico": [{"autor": "Gestora Patrimônio", "texto": "Em análise", "quando": NOW - timedelta(days=1)}]},
    {"id": 9002, "assunto": "Notebook lento", "descricao": "T14 travando", "origem": "Suporte",
     "prioridade": "média", "status": "em_atendimento", "aberto_em": NOW - timedelta(days=1), "ativo_id": 101,
     "historico": [{"autor": "Colaborador", "texto": "Começou hoje", "quando": NOW - timedelta(hours=20)}]},
    {"id": 9003, "assunto": "Acesso ao ERP", "descricao": "Erro de permissão", "origem": "ERP",
     "prioridade": "baixa", "status": "resolvido", "aberto_em": NOW - timedelta(days=3), "ativo_id": None,
     "historico": [{"autor": "Admin", "texto": "Permissões ajustadas", "quando": NOW - timedelta(days=2)}]},
]


def indicadores_chamados(chamados=None):
    """
    Retorna dois dicionários:
      - por_status
      - por_prioridade
    Aceita opcionalmente uma lista de chamados; se None, usa MOCK_CHAMADOS.
    """
    data = chamados if chamados is not None else MOCK_CHAMADOS
    por_status = Counter((c.get("status") or "").lower() for c in data)
    por_prioridade = Counter((c.get("prioridade") or "").lower() for c in data)
    return dict(por_status), dict(por_prioridade)

def indicadores_por_agente(chamados):
    """Retorna métricas por agente: fechados %, pendentes e % dentro do SLA."""
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M"
    por = {}

    for c in chamados:
        ag = c.get("agente", "Sem atribuição")
        m = por.setdefault(ag, {"total": 0, "fechados": 0, "pendentes": 0, "dentro_sla": 0})
        m["total"] += 1

        status = (c.get("status") or "").lower()
        if status in ("resolvido", "fechado"):
            m["fechados"] += 1
            # regra de SLA
            inside = c.get("dentro_sla")
            if inside is None:
                sla = c.get("sla_horas")
                ab, fe = c.get("aberto_em"), c.get("fechado_em")
                ok = False
                try:
                    if sla and ab and fe:
                        ok = (datetime.strptime(fe, fmt) - datetime.strptime(ab, fmt)).total_seconds() <= sla * 3600
                except Exception:
                    ok = False
                inside = ok
            m["dentro_sla"] += 1 if inside else 0
        else:
            m["pendentes"] += 1

    rows = []
    for ag, m in por.items():
        fechados_pct = (m["fechados"] / m["total"] * 100) if m["total"] else 0
        sla_pct = (m["dentro_sla"] / m["fechados"] * 100) if m["fechados"] else 0
        rows.append({
            "agente": ag,
            "total": m["total"],
            "fechados": m["fechados"],
            "fechados_pct": round(fechados_pct, 1),
            "pendentes": m["pendentes"],
            "sla_pct": round(sla_pct, 1),
        })

    rows.sort(key=lambda r: (-r["fechados"], r["agente"]))
    return rows

# ---------------- PROJETOS (MOCK) ----------------
MOCK_PROJETOS = [
    {"id": 1, "titulo": "Upgrade Wi-Fi",        "responsavel": "Suporte 1",      "status": "em_andamento", "area": "Infraestrutura de T.I", "percentual": 48.7, "prazo": "2025-10-25", "atrasado": False},
    {"id": 2, "titulo": "Portal Compras",       "responsavel": "Suporte 2",      "status": "em_andamento", "area": "Administrativo",       "percentual": 23.0, "prazo": "2025-10-12", "atrasado": True},
    {"id": 3, "titulo": "Dash Operacional",     "responsavel": "Suporte 3",   "status": "em_andamento", "area": "Comercial",            "percentual": 22.5, "prazo": "2025-10-30", "atrasado": False},
    {"id": 4, "titulo": "MES – Produção",       "responsavel": "Suporte 4",      "status": "nao_iniciado", "area": "Controle Industrial",  "percentual": 0.0,  "prazo": "2025-11-30", "atrasado": False},
    {"id": 5, "titulo": "App Vendas",           "responsavel": "Suporte 5",      "status": "nao_iniciado", "area": "Comercial",            "percentual": 0.0,  "prazo": "2025-11-15", "atrasado": False},
    {"id": 6, "titulo": "ETL Financeiro",       "responsavel": "Suporte 6",    "status": "em_andamento", "area": "Administrativo",       "percentual": 4.2,  "prazo": "2025-10-05", "atrasado": True},
    {"id": 7, "titulo": "CMMS Manutenção",      "responsavel": "Suporte 7","status": "concluido",   "area": "Controle Industrial",  "percentual": 100,  "prazo": "2025-09-20", "atrasado": False},
    {"id": 8, "titulo": "Upgrade ERP",          "responsavel": "Suporte 2",   "status": "concluido",    "area": "Administrativo",       "percentual": 100,  "prazo": "2025-09-05", "atrasado": False},
    {"id": 9, "titulo": "BI de Produção",       "responsavel": "Suporte 1",      "status": "em_andamento", "area": "Infraestrutura de T.I","percentual": 25.9, "prazo": "2025-10-28", "atrasado": False},
    {"id":10, "titulo": "Integração WMS",       "responsavel": "Suporte 5",      "status": "concluido",    "area": "Controle Industrial",  "percentual": 100,  "prazo": "2025-08-30", "atrasado": False},
]

def proj_kpis(projs):
    t = len(projs)
    concl = sum(1 for p in projs if p["status"] == "concluido")
    anda  = sum(1 for p in projs if p["status"] == "em_andamento")
    nao   = sum(1 for p in projs if p["status"] == "nao_iniciado")
    atras = sum(1 for p in projs if p.get("atrasado"))
    no_prazo = t - atras
    pct_conc = round((concl / t * 100) if t else 0.0, 1)
    return {
        "total": t, "concluidos": concl, "em_andamento": anda, "nao_iniciados": nao,
        "atrasados": atras, "no_prazo": no_prazo, "pct_concluido": pct_conc
    }

def proj_por_status_segments(projs):
    counts = Counter(p["status"] for p in projs)
    total = sum(counts.values()) or 1
    color_map = {
        "em_andamento": "#60a5fa",  # azul
        "concluido":    "#10b981",  # verde
        "nao_iniciado": "#94a3b8",  # cinza
    }
    acc = 0.0
    segs = []
    for label, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = c / total * 100
        segs.append({"label": label, "count": c, "pct": round(pct,1),
                     "start": round(acc,4), "end": round(acc+pct,4),
                     "color": color_map.get(label, "#a78bfa")})
        acc += pct
    return segs, 100.0

def proj_por_responsavel(projs):
    m = {}
    for p in projs:
        r = p["responsavel"]
        mm = m.setdefault(r, {"total":0, "concl":0})
        mm["total"] += 1
        mm["concl"] += 1 if p["status"] == "concluido" else 0
    rows = []
    for r, d in m.items():
        pct = (d["concl"]/d["total"]*100) if d["total"] else 0
        rows.append({"resp": r, "pct": round(pct,1), "concl": d["concl"], "total": d["total"]})
    rows.sort(key=lambda x: (-x["pct"], x["resp"]))
    return rows

def proj_por_area(projs):
    m = {}
    for p in projs:
        a = p["area"]
        d = m.setdefault(a, {"total":0, "anda":0, "concl":0})
        d["total"] += 1
        d["concl"] += 1 if p["status"] == "concluido" else 0
        d["anda"]  += 1 if p["status"] == "em_andamento" else 0
    out = []
    for a, d in m.items():
        pct = (d["concl"]/d["total"]*100) if d["total"] else 0
        out.append({"area": a, "total": d["total"], "anda": d["anda"], "concl": d["concl"], "pct": round(pct,1)})
    out.sort(key=lambda r: (-r["pct"], r["area"]))
    return out
