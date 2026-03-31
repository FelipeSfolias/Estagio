import re
import random
import time
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .authz import tier_required
from .forms import (
    AbrirChamadoForm,
    AtivoForm,
    ChamadoPublicForm,
    ItemEstoqueForm,
    LocalForm,
    ResponderChamadoForm,
    UsuarioForm,
    TIPOS_ATIVO,
)
from .mock_data import (
    MOCK_ATIVOS,
    MOCK_CHAMADOS,
    MOCK_ITENS_ESTOQUE,
    MOCK_LOCAIS,
    MOCK_PROJETOS,
    MOCK_USUARIOS,
    indicadores_chamados as calc_indicadores_chamados,
    indicadores_por_agente,
    proj_kpis,
    proj_por_area,
    proj_por_responsavel,
    proj_por_status_segments,
)

# ============================================================
# CONSTANTES / HELPERS
# ============================================================

SETOR_OPCOES = ["Produção", "PPCP", "Demanda", "Compras", "TI", "Estoque", "Engenharia", "Modelagem", "Corte"]


def next_patrimonio(ativos):
    nums = []
    for a in ativos:
        m = re.search(r'(\d{4})$', str(a.get("patrimonio", "")))
        if m:
            nums.append(int(m.group(1)))
    prox = (max(nums) + 1) if nums else 1
    return f"PAT-{prox:04d}"


def _format_patrimonio(raw: str):
    raw = (raw or "").strip().upper()
    if re.fullmatch(r"\d{4}", raw):
        return f"PAT-{int(raw):04d}"
    m = re.fullmatch(r"PAT-(\d{4})", raw)
    if m:
        return f"PAT-{m.group(1)}"
    return None


def _build_segments(items):
    segs, cursor = [], 0.0
    for label, color, pct, count in items:
        segs.append({
            "label": label, "color": color,
            "pct": round(float(pct), 1), "count": int(count),
            "start": round(cursor, 1), "end": round(cursor + float(pct), 1),
        })
        cursor += float(pct)
    return segs


def _build_pie_tipos(chamados, pct_override=None, abs_total_override=None):
    color_map = {
        "ERP": "#3b82f6", "Manutenção": "#f59e0b",
        "Suporte": "#10b981", "Infra": "#a3e635", "Outros": "#64748b",
    }
    palette = ["#a78bfa", "#f472b6", "#22d3ee", "#93c5fd", "#fca5a5"]
    segments, acc, extra_i = [], 0.0, 0

    if pct_override:
        abs_total = abs_total_override if abs_total_override is not None else len(chamados)
        for label, pct in pct_override.items():
            color = color_map.get(label) or palette[extra_i % len(palette)]
            extra_i += (0 if color_map.get(label) else 1)
            segments.append({
                "label": label, "count": None,
                "pct": round(float(pct), 1),
                "start": round(acc, 4), "end": round(acc + float(pct), 4),
                "color": color,
            })
            acc += float(pct)
        return segments, 100.0, abs_total

    counts = Counter((c.get("origem") or "Outros") for c in chamados)
    abs_total = sum(counts.values()) or 1
    for label, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = (count / abs_total) * 100.0
        color = color_map.get(label) or palette[extra_i % len(palette)]
        extra_i += 1
        segments.append({
            "label": label, "count": count, "pct": round(pct, 1),
            "start": round(acc, 4), "end": round(acc + pct, 4), "color": color,
        })
        acc += pct
    return segments, 100.0, abs_total


def _build_pie_conclusao(chamados, counts_override=None, abs_total_override=None):
    if counts_override:
        concl = int(counts_override.get("Concluídos", 0))
        pend = int(counts_override.get("Não concluídos", 0))
        total_abs = concl + pend or 1
    else:
        total_abs = len(chamados) or 1
        concl = sum(1 for c in chamados if (c.get("status") or "").lower() in ("resolvido", "fechado"))
        pend = total_abs - concl

    segments, acc = [], 0.0
    for label, count, color in [
        ("Concluídos", concl, "#10b981"),
        ("Não concluídos", pend, "#ef4444"),
    ]:
        pct = (count / total_abs) * 100.0
        segments.append({
            "label": label, "count": count, "pct": round(pct, 1),
            "start": round(acc, 4), "end": round(acc + pct, 4), "color": color,
        })
        acc += pct
    final_abs_total = abs_total_override if abs_total_override is not None else total_abs
    return segments, 100.0, final_abs_total


def _get_projeto_by_id(pk: int):
    for p in MOCK_PROJETOS:
        if p["id"] == pk:
            return p
    return None


def _chat_reply_and_state(msg, state):
    m = (msg or "").strip()
    ml = m.lower()

    if any(w in ml for w in ["ajuda", "opções", "opcoes", "menu"]):
        return (
            "Posso ajudar com:\n"
            "• diagnosticar problemas (ex.: \"wifi caiu\", \"sem acesso ao ERP\")\n"
            "• abrir um chamado (diga \"abrir chamado\")\n"
            "• acompanhar chamados (acesse: Meus Chamados)"
        ), state

    if "wifi" in ml or "wi-fi" in ml:
        return (
            "Entendi: problema de Wi-Fi. Tente:\n"
            "1) Reiniciar o adaptador de rede\n"
            "2) Esquecer e reconectar à rede\n"
            "3) Se persistir, digite **abrir chamado**"
        ), state

    if "erp" in ml:
        return (
            "Sem acesso ao ERP? Verifique VPN/AD. Se continuar, digite **abrir chamado** "
            "para eu registrar pro time de TI."
        ), state

    if "notebook" in ml or "lento" in ml or "travando" in ml:
        return (
            "Notebook lento: feche apps pesados, limpe arquivos temporários. "
            "Se não resolver, digite **abrir chamado**."
        ), state

    if "abrir chamado" in ml or "criar chamado" in ml:
        state = {"step": "assunto"}
        return "Perfeito, vamos abrir um chamado! Qual é o **assunto**?", state

    if state and state.get("step") == "assunto":
        state["assunto"] = m
        state["step"] = "origem"
        return "Certo. Qual é a **origem**? (Infra | Suporte | ERP | Manutenção | Outros)", state

    if state and state.get("step") == "origem":
        mapa = {
            "infra": "Infra", "suporte": "Suporte", "erp": "ERP",
            "manutencao": "Manutenção", "manutenção": "Manutenção", "outros": "Outros",
        }
        state["origem"] = mapa.get(m.lower(), m.capitalize() or "Outros")
        state["step"] = "descricao"
        return "Anotei. Agora descreva o problema com **detalhes**:", state

    if state and state.get("step") == "descricao":
        state["descricao"] = m
        novo_id = (max(c["id"] for c in MOCK_CHAMADOS) + 1) if MOCK_CHAMADOS else 9001
        payload = {
            "id": novo_id,
            "assunto": state["assunto"],
            "descricao": state["descricao"],
            "origem": state["origem"],
            "prioridade": "média",
            "status": "aberto",
            "aberto_em": timezone.now(),
            "aberto_por": state.get("username", "colaborador"),
            "ativo_id": None,
            "historico": [],
        }
        MOCK_CHAMADOS.append(payload)
        state = {}
        return (
            f"Chamado **#{novo_id}** aberto!\n"
            f"Assunto: {payload['assunto']}\n"
            f"Origem: {payload['origem']}\n"
            "Você pode acompanhar em **Meus Chamados**."
        ), state

    return (
        "Não tenho certeza se entendi. Você pode tentar: **abrir chamado**, "
        "**ajuda** ou descrever o problema (ex.: \"wifi caiu\")."
    ), state


# ============================================================
# AUTENTICAÇÃO
# ============================================================

class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        if self.request.POST.get("remember_me"):
            self.request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            self.request.session.set_expiry(0)
        return resp


def password_reset_start(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        code = f"{random.randint(0, 999999):06d}"
        request.session["pwd_reset_email"] = email
        request.session["pwd_reset_code"] = code
        request.session["pwd_reset_expires"] = time.time() + 600
        print(f"[DEBUG] Código de reset para {email}: {code}")
        messages.info(request, "Enviamos um código de verificação para seu e-mail.")
        return redirect("accounts:password_reset_code")
    return render(request, "registration/password_reset_start.html")


def password_reset_code(request):
    email = request.session.get("pwd_reset_email")
    code_expected = request.session.get("pwd_reset_code")
    expires = request.session.get("pwd_reset_expires", 0)

    if not email or not code_expected:
        messages.error(request, "Sessão expirada. Solicite novamente.")
        return redirect("accounts:password_reset_start")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        p1 = request.POST.get("password1", "")
        p2 = request.POST.get("password2", "")

        if time.time() > float(expires):
            messages.error(request, "Código expirado. Solicite novamente.")
            return redirect("accounts:password_reset_start")

        if code != code_expected:
            messages.error(request, "Código inválido.")
            return render(request, "registration/password_reset_code.html", {"dev_code": code_expected})

        if not p1 or p1 != p2:
            messages.error(request, "As senhas não conferem.")
            return render(request, "registration/password_reset_code.html", {"dev_code": code_expected})

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            messages.success(request, "Senha alterada. Faça login.")
            for k in ("pwd_reset_email", "pwd_reset_code", "pwd_reset_expires"):
                request.session.pop(k, None)
            return redirect("accounts:login")

        user.set_password(p1)
        user.save()
        for k in ("pwd_reset_email", "pwd_reset_code", "pwd_reset_expires"):
            request.session.pop(k, None)
        messages.success(request, "Senha redefinida com sucesso. Faça login.")
        return redirect("accounts:login")

    return render(request, "registration/password_reset_code.html", {"dev_code": code_expected})


@login_required
def pos_login_redirect(request):
    u = request.user
    if u.is_superuser or u.groups.filter(name__iexact="admin").exists():
        return redirect("core:dashboard")
    if u.groups.filter(name__iexact="suporte").exists():
        return redirect("core:chamados_indicadores")
    if u.groups.filter(name__iexact="colaborador").exists():
        return redirect("core:chamado_criar_tier")
    return redirect("core:chamado_criar_tier")


# ============================================================
# ADMIN ONLY
# ============================================================

@login_required
@tier_required("admin")
def dashboard(request):
    by_status, by_prio = calc_indicadores_chamados(MOCK_CHAMADOS)
    recentes = sorted(MOCK_CHAMADOS, key=lambda c: c["aberto_em"], reverse=True)[:5]

    pct_override = {"Infra": 54.0, "Suporte": 16.0, "ERP": 30.0}
    tipos_segments, _t, tipos_total_abs = _build_pie_tipos(
        MOCK_CHAMADOS, pct_override=pct_override, abs_total_override=200
    )
    concl_segments, _c, concl_total_abs = _build_pie_conclusao(
        MOCK_CHAMADOS,
        counts_override={"Concluídos": 200, "Não concluídos": 400},
        abs_total_override=600,
    )

    return render(request, "dashboard.html", {
        "kpis_status": by_status,
        "kpis_prioridade": by_prio,
        "recentes": recentes,
        "tipos_segments": tipos_segments,
        "tipos_total_abs": tipos_total_abs,
        "concl_segments": concl_segments,
        "concl_total_abs": concl_total_abs,
    })


@login_required
@tier_required("admin")
def cad_usuarios(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            novo_id = (max([u["id"] for u in MOCK_USUARIOS]) + 1) if MOCK_USUARIOS else 1
            MOCK_USUARIOS.append({
                "id": novo_id,
                "nome": form.cleaned_data["nome"],
                "email": form.cleaned_data["email"],
                "nome_usuario": form.cleaned_data["nome_usuario"],
                "role": form.cleaned_data["role"],
                "ativo": form.cleaned_data["ativo"],
            })
            return redirect("core:cad_usuarios")
    else:
        form = UsuarioForm()

    q = (request.GET.get("q") or "").lower().strip()
    f_role = (request.GET.get("role") or "").lower().strip()
    f_ativo = (request.GET.get("ativo") or "").strip()
    f_id = (request.GET.get("id") or "").strip()

    dados = list(MOCK_USUARIOS)
    if q:
        dados = [u for u in dados if q in u["nome"].lower()
                 or q in u["email"].lower() or q in u["nome_usuario"].lower()]
    if f_role:
        dados = [u for u in dados if (u.get("role", "").lower() == f_role)]
    if f_ativo in ("sim", "nao"):
        want = (f_ativo == "sim")
        dados = [u for u in dados if bool(u.get("ativo")) == want]
    if f_id:
        try:
            iid = int(f_id)
            dados = [u for u in dados if u["id"] == iid]
        except ValueError:
            dados = []

    roles = sorted({(u.get("role") or "") for u in MOCK_USUARIOS if u.get("role")})
    return render(request, "cadastros/usuarios.html", {
        "form": form, "usuarios": dados, "roles": roles,
        "sel_role": f_role, "sel_ativo": f_ativo, "sel_id": f_id,
    })


@login_required
@tier_required("admin")
def usuario_editar(request, uid: int):
    if request.method == "POST":
        messages.success(request, f"Usuário #{uid} atualizado (mock).")
        return redirect("core:cad_usuarios")
    messages.info(request, f"Edição do usuário #{uid} (mock).")
    return redirect("core:cad_usuarios")


@login_required
@tier_required("admin")
def usuario_excluir(request, uid: int):
    idx = next((i for i, u in enumerate(MOCK_USUARIOS) if u.get("id") == uid), None)
    if idx is None:
        messages.error(request, f"Usuário #{uid} não encontrado.")
        return redirect("core:cad_usuarios")
    nome = MOCK_USUARIOS[idx].get("nome") or f"#{uid}"
    del MOCK_USUARIOS[idx]
    messages.success(request, f"Usuário '{nome}' excluído (mock).")
    return redirect("core:cad_usuarios")


@login_required
@tier_required("admin")
def cad_locais(request):
    if request.method == "POST":
        form = LocalForm(request.POST)
        if form.is_valid():
            novo_id = (max([l["id"] for l in MOCK_LOCAIS]) + 1) if MOCK_LOCAIS else 10
            MOCK_LOCAIS.append({
                "id": novo_id,
                "codigo": form.cleaned_data["codigo"],
                "nome": form.cleaned_data["nome"],
                "tipo": form.cleaned_data["tipo"],
                "pai_id": form.cleaned_data["pai_id"] or None,
            })
            return redirect("core:cad_locais")
    else:
        form = LocalForm()

    q = (request.GET.get("q") or "").lower().strip()
    f_tipo = (request.GET.get("tipo") or "").lower().strip()
    f_pai = (request.GET.get("pai") or "").strip()
    f_id = (request.GET.get("id") or "").strip()

    dados = list(MOCK_LOCAIS)
    if q:
        dados = [l for l in dados if q in l["codigo"].lower()
                 or q in l["nome"].lower() or q in (l.get("tipo", "").lower())]
    if f_tipo:
        dados = [l for l in dados if (l.get("tipo", "").lower() == f_tipo)]
    if f_pai == "raiz":
        dados = [l for l in dados if not l.get("pai_id")]
    elif f_pai == "compai":
        dados = [l for l in dados if l.get("pai_id")]
    if f_id:
        try:
            iid = int(f_id)
            dados = [l for l in dados if l["id"] == iid]
        except ValueError:
            dados = []

    tipos = sorted({(l.get("tipo") or "") for l in MOCK_LOCAIS if l.get("tipo")})
    return render(request, "cadastros/locais.html", {
        "form": form, "locais": dados, "tipos": tipos,
        "sel_tipo": f_tipo, "sel_pai": f_pai, "sel_id": f_id,
    })


@login_required
@tier_required("admin")
def local_editar(request, lid: int):
    if request.method == "POST":
        messages.success(request, f"Local #{lid} atualizado (mock).")
        return redirect("core:cad_locais")
    messages.info(request, f"Edição do local #{lid} (mock).")
    return redirect("core:cad_locais")


@login_required
@tier_required("admin")
@require_POST
def local_excluir(request, lid: int):
    idx = next((i for i, x in enumerate(MOCK_LOCAIS) if x.get("id") == lid), None)
    if idx is None:
        messages.error(request, f"Local #{lid} não encontrado.")
    else:
        nome = MOCK_LOCAIS[idx].get("nome") or f"#{lid}"
        del MOCK_LOCAIS[idx]
        messages.success(request, f"Local '{nome}' excluído (mock).")
    return redirect("core:cad_locais")


@login_required
@tier_required("admin")
def cad_ativos(request):
    if request.method == "POST":
        form = AtivoForm(request.POST)
        if form.is_valid():
            pat = _format_patrimonio(form.cleaned_data["patrimonio"])
            if not pat:
                messages.error(request, "Patrimônio inválido. Use 4 dígitos (ex.: 0007) ou PAT-0007.")
            else:
                novo_id = (max([a["id"] for a in MOCK_ATIVOS]) + 1) if MOCK_ATIVOS else 100
                MOCK_ATIVOS.append({
                    "id": novo_id,
                    "patrimonio": pat,
                    "numero_serie": form.cleaned_data["numero_serie"],
                    "modelo": form.cleaned_data["modelo"],
                    "categoria": form.cleaned_data["categoria"],
                    "estado": form.cleaned_data["estado"],
                    "local_id": int(form.cleaned_data["local_id"]),
                    "custodiante": form.cleaned_data["custodiante"] or "-",
                })
                messages.success(request, f"Ativo {pat} salvo (mock).")
                return redirect("core:cad_ativos")
    else:
        form = AtivoForm(initial={"patrimonio": next_patrimonio(MOCK_ATIVOS)})

    q = (request.GET.get("q") or "").lower().strip()
    f_tipo = (request.GET.get("tipo") or "").strip()
    f_setor = (request.GET.get("setor") or "").lower().strip()
    f_id = (request.GET.get("id") or "").strip()

    dados = list(MOCK_ATIVOS)
    if q:
        dados = [a for a in dados if q in a["patrimonio"].lower()
                 or q in a["modelo"].lower() or q in a["numero_serie"].lower()]
    if f_tipo:
        dados = [a for a in dados if a["categoria"].lower() == f_tipo.lower()]
    if f_setor:
        id2nome = {l["id"]: l["nome"].lower() for l in MOCK_LOCAIS}
        dados = [a for a in dados if f_setor in id2nome.get(a.get("local_id"), "")]
    if f_id:
        try:
            fid = int(f_id)
            dados = [a for a in dados if a["id"] == fid]
        except ValueError:
            dados = []

    return render(request, "cadastros/ativos.html", {
        "form": form, "ativos": dados, "locais": MOCK_LOCAIS,
        "tipos": [t[0] for t in TIPOS_ATIVO], "setores": SETOR_OPCOES,
        "sel_tipo": f_tipo, "sel_setor": f_setor, "sel_id": f_id,
    })


@login_required
@tier_required("admin")
def ativo_editar(request, aid: int):
    if request.method == "POST":
        messages.success(request, f"Ativo #{aid} atualizado (mock).")
        return redirect("core:cad_ativos")
    messages.info(request, f"Edição do ativo #{aid} (mock).")
    return redirect("core:cad_ativos")


@login_required
@tier_required("admin")
@require_POST
def ativo_excluir(request, aid: int):
    idx = next((i for i, x in enumerate(MOCK_ATIVOS) if x.get("id") == aid), None)
    if idx is None:
        messages.error(request, f"Ativo #{aid} não encontrado.")
    else:
        del MOCK_ATIVOS[idx]
        messages.success(request, f"Ativo #{aid} excluído (mock).")
    return redirect("core:cad_ativos")


@login_required
@tier_required("admin")
def cad_itens_estoque(request):
    if request.method == "POST":
        form = ItemEstoqueForm(request.POST)
        if form.is_valid():
            novo_id = (max([i["id"] for i in MOCK_ITENS_ESTOQUE]) + 1) if MOCK_ITENS_ESTOQUE else 1
            MOCK_ITENS_ESTOQUE.append({
                "id": novo_id,
                "sku": form.cleaned_data["sku"],
                "nome": form.cleaned_data["nome"],
                "unidade": form.cleaned_data["unidade"],
                "nivel_minimo": form.cleaned_data["nivel_minimo"],
                "qtde": form.cleaned_data["qtde"],
            })
            return redirect("core:cad_itens_estoque")
    else:
        form = ItemEstoqueForm()

    q = (request.GET.get("q") or "").lower().strip()
    f_uni = (request.GET.get("unidade") or "").lower().strip()
    f_low = (request.GET.get("low") or "").strip()
    f_id = (request.GET.get("id") or "").strip()

    dados = list(MOCK_ITENS_ESTOQUE)
    if q:
        dados = [i for i in dados if q in i["sku"].lower() or q in i["nome"].lower()]
    if f_uni:
        dados = [i for i in dados if (i.get("unidade", "").lower() == f_uni)]
    if f_low == "sim":
        dados = [i for i in dados if int(i.get("qtde", 0)) <= int(i.get("nivel_minimo", 0))]
    if f_id:
        try:
            iid = int(f_id)
            dados = [i for i in dados if i["id"] == iid]
        except ValueError:
            dados = []

    unidades = sorted({(i.get("unidade") or "") for i in MOCK_ITENS_ESTOQUE if i.get("unidade")})
    return render(request, "cadastros/itens_estoque.html", {
        "form": form, "itens": dados, "unidades": unidades,
        "sel_unidade": f_uni, "sel_low": f_low, "sel_id": f_id,
    })


@login_required
@tier_required("admin")
def item_editar(request, iid: int):
    if request.method == "POST":
        messages.success(request, f"Item #{iid} atualizado (mock).")
        return redirect("core:cad_itens_estoque")
    messages.info(request, f"Edição do item #{iid} (mock).")
    return redirect("core:cad_itens_estoque")


@login_required
@tier_required("admin")
@require_POST
def item_excluir(request, iid: int):
    idx = next((i for i, x in enumerate(MOCK_ITENS_ESTOQUE) if x.get("id") == iid), None)
    if idx is None:
        messages.error(request, f"Item #{iid} não encontrado.")
    else:
        nome = MOCK_ITENS_ESTOQUE[idx].get("nome") or f"#{iid}"
        del MOCK_ITENS_ESTOQUE[idx]
        messages.success(request, f"Item '{nome}' excluído (mock).")
    return redirect("core:cad_itens_estoque")


@login_required
@tier_required("admin")
def patrimonios_lista(request):
    q = request.GET.get("q", "").strip().lower()
    dados = MOCK_ATIVOS
    if q:
        dados = [a for a in MOCK_ATIVOS if q in a["patrimonio"].lower()
                 or q in a["modelo"].lower() or q in a["numero_serie"].lower()]
    return render(request, "patrimonios/lista.html", {
        "ativos": dados, "locais": MOCK_LOCAIS, "busca": q,
    })


# ============================================================
# SUPORTE + ADMIN
# ============================================================

@login_required
@tier_required("suporte", "admin")
def chamados_indicadores(request):
    by_status, by_prio = calc_indicadores_chamados(MOCK_CHAMADOS)
    agentes = indicadores_por_agente(MOCK_CHAMADOS)

    pct_override = {"Infra": 54.0, "Suporte": 16.0, "ERP": 30.0}
    tipos_segments, _t, tipos_total_abs = _build_pie_tipos(
        MOCK_CHAMADOS, pct_override=pct_override, abs_total_override=200
    )
    concl_segments, _c, concl_total_abs = _build_pie_conclusao(
        MOCK_CHAMADOS,
        counts_override={"Concluídos": 200, "Não concluídos": 400},
        abs_total_override=600,
    )

    return render(request, "chamados/indicadores.html", {
        "by_status": by_status, "by_prio": by_prio, "agentes": agentes,
        "tipos_segments": tipos_segments, "tipos_total_abs": tipos_total_abs,
        "concl_segments": concl_segments, "concl_total_abs": concl_total_abs,
        "lista": MOCK_CHAMADOS,
    })


@login_required
@tier_required("suporte", "admin")
def projetos_kanban(request):
    meta_cols = [
        {"key": "nao_iniciado", "title": "Não iniciado"},
        {"key": "em_andamento", "title": "Em andamento"},
        {"key": "concluido", "title": "Concluído"},
    ]
    cols_map = {
        "nao_iniciado": [p for p in MOCK_PROJETOS if p["status"] == "nao_iniciado"],
        "em_andamento": [p for p in MOCK_PROJETOS if p["status"] == "em_andamento"],
        "concluido": [p for p in MOCK_PROJETOS if p["status"] == "concluido"],
    }
    q = (request.GET.get("q") or "").lower().strip()
    if q:
        for k in list(cols_map.keys()):
            cols_map[k] = [
                p for p in cols_map[k]
                if q in p["titulo"].lower() or q in p["responsavel"].lower()
            ]
    kanban_cols = [
        {"key": m["key"], "title": m["title"], "items": cols_map[m["key"]]}
        for m in meta_cols
    ]
    return render(request, "projetos/kanban.html", {"kanban_cols": kanban_cols})


@login_required
@tier_required("suporte", "admin")
def projetos_indicadores(request):
    kpis = proj_kpis(MOCK_PROJETOS)
    status_segs, status_total = proj_por_status_segments(MOCK_PROJETOS)
    por_resp = proj_por_responsavel(MOCK_PROJETOS)
    por_area = proj_por_area(MOCK_PROJETOS)

    concl_pct = kpis["pct_concluido"]
    concl_segments = [
        {"label": "Concluídos", "start": 0, "end": concl_pct, "pct": round(concl_pct, 1), "color": "#10b981"},
        {"label": "Demais", "start": concl_pct, "end": 100, "pct": round(100 - concl_pct, 1), "color": "#e5e7eb"},
    ]
    return render(request, "projetos/indicadores.html", {
        "kpis": kpis,
        "status_segments": status_segs, "status_total": status_total,
        "concl_segments": concl_segments,
        "por_resp": por_resp,
        "por_area": por_area,
    })


@login_required
@tier_required("suporte", "admin")
def card_editar(request, pk):
    projeto = _get_projeto_by_id(pk)
    if not projeto:
        raise Http404("Projeto não encontrado")

    if request.method == "POST":
        projeto["titulo"] = request.POST.get("titulo", projeto["titulo"])
        projeto["responsavel"] = request.POST.get("responsavel", projeto["responsavel"])
        projeto["area"] = request.POST.get("area", projeto["area"])
        projeto["status"] = request.POST.get("status", projeto["status"])
        projeto["prazo"] = request.POST.get("prazo", projeto.get("prazo", ""))
        percentual_raw = request.POST.get("percentual")
        if percentual_raw:
            try:
                projeto["percentual"] = float(percentual_raw.replace(",", "."))
            except ValueError:
                pass
        projeto["cor"] = request.POST.get("cor", projeto.get("cor", ""))
        return redirect("core:projetos_kanban")

    return render(request, "projetos/card_editar.html", {"projeto": projeto})


# ============================================================
# COLABORADOR + SUPORTE + ADMIN
# ============================================================

@login_required
@tier_required("colaborador", "suporte", "admin")
def chamado_novo(request):
    form = AbrirChamadoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        novo_id = (max(c["id"] for c in MOCK_CHAMADOS) + 1) if MOCK_CHAMADOS else 9001
        MOCK_CHAMADOS.append({
            "id": novo_id,
            "assunto": form.cleaned_data["assunto"],
            "descricao": form.cleaned_data["descricao"],
            "origem": form.cleaned_data["origem"],
            "prioridade": form.cleaned_data["prioridade"],
            "status": "aberto",
            "aberto_em": timezone.now(),
            "aberto_por": request.user.username,
            "ativo_id": form.cleaned_data.get("ativo_id") or None,
            "historico": [],
        })
        messages.success(request, f"Chamado #{novo_id} aberto com sucesso.")
        return redirect("core:meus_chamados")
    return render(request, "chamados/novo.html", {"form": form})


@login_required
@tier_required("colaborador", "suporte", "admin")
def chamado_criar_tier(request):
    form = ChamadoPublicForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        novo_id = (max(c["id"] for c in MOCK_CHAMADOS) + 1) if MOCK_CHAMADOS else 9001
        MOCK_CHAMADOS.append({
            "id": novo_id,
            "assunto": form.cleaned_data["assunto"],
            "descricao": form.cleaned_data["descricao"],
            "origem": form.cleaned_data["origem"],
            "prioridade": form.cleaned_data["prioridade"],
            "status": "aberto",
            "aberto_em": timezone.now(),
            "aberto_por": request.user.username,
            "ativo_id": form.cleaned_data.get("ativo_id") or None,
            "historico": [],
        })
        messages.success(request, f"Chamado #{novo_id} aberto com sucesso.")
        return redirect("core:meus_chamados")
    return render(request, "chamados/abrir_tier.html", {"form": form})


@login_required
@tier_required("colaborador", "suporte", "admin")
def meus_chamados(request):
    user = request.user
    is_admin_suporte = user.is_superuser or user.groups.filter(name__in=["admin", "suporte"]).exists()

    # Suporte/admin vê todos; colaborador só os seus
    if is_admin_suporte:
        chamados = list(MOCK_CHAMADOS)
    else:
        chamados = [c for c in MOCK_CHAMADOS if c.get("aberto_por") == user.username]

    status_sel = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip().lower()
    if status_sel:
        chamados = [c for c in chamados if c.get("status") == status_sel]
    if q:
        chamados = [c for c in chamados if q in c["assunto"].lower() or q in str(c["id"])]

    return render(request, "chamados/meus.html", {
        "chamados": chamados,
        "status_sel": status_sel,
        "q": q,
    })


@login_required
@tier_required("colaborador", "suporte", "admin")
def chamado_detalhe(request, cid: int):
    user = request.user
    is_admin_suporte = user.is_superuser or user.groups.filter(name__in=["admin", "suporte"]).exists()

    chamado = next((c for c in MOCK_CHAMADOS if c["id"] == cid), None)
    if not chamado:
        messages.error(request, "Chamado não encontrado.")
        return redirect("core:meus_chamados")

    # Colaborador só pode ver os próprios chamados
    if not is_admin_suporte and chamado.get("aberto_por") != user.username:
        messages.error(request, "Sem permissão para acessar este chamado.")
        return redirect("core:meus_chamados")

    form = ResponderChamadoForm(
        request.POST or None,
        initial={"novo_status": chamado.get("status")},
    )
    if request.method == "POST" and form.is_valid() and is_admin_suporte:
        chamado["status"] = form.cleaned_data["novo_status"]
        comentario = form.cleaned_data.get("comentario", "").strip()
        if comentario:
            chamado.setdefault("historico", []).append({
                "autor": user.get_full_name() or user.username,
                "texto": comentario,
                "quando": timezone.now(),
            })
        messages.success(request, "Ação registrada.")
        return redirect("core:chamado_detalhe", cid=cid)

    return render(request, "chamados/detalhe.html", {
        "chamado": chamado,
        "form": form,
        "pode_responder": is_admin_suporte,
    })


# ============================================================
# COLABORADOR ONLY
# ============================================================

@login_required
@tier_required("colaborador")
def assistente(request):
    msgs = request.session.get("chat_msgs", [])
    if not msgs:
        msgs = [{
            "de": "bot",
            "texto": "Olá! Sou seu assistente. Posso **abrir chamado** ou ajudar no diagnóstico. Diga *ajuda* para ver opções.",
        }]
        request.session["chat_msgs"] = msgs

    if request.method == "POST":
        user_msg = (request.POST.get("msg") or "").strip()
        if user_msg:
            state = request.session.get("chat_state", {})
            state["username"] = request.user.username
            msgs.append({"de": "user", "texto": user_msg})
            bot_reply, state = _chat_reply_and_state(user_msg, state)
            msgs.append({"de": "bot", "texto": bot_reply})
            request.session["chat_msgs"] = msgs
            request.session["chat_state"] = state
        return redirect("core:assistente_chat")

    return render(request, "chat/assistente.html", {"msgs": msgs})
