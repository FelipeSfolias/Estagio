from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Ativo, Chamado, HistoricoChamado, ItemEstoque, Local, Projeto
from .serializers import (
    AtivoSerializer,
    ChamadoSerializer,
    HistoricoChamadoSerializer,
    ItemEstoqueSerializer,
    LocalSerializer,
    ProjetoSerializer,
    UsuarioSerializer,
)


class IsAdminGroup(IsAuthenticated):
    """Permite acesso somente a membros do grupo 'admin'."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser or request.user.groups.filter(name="admin").exists()
        )


class IsSupporteOrAdmin(IsAuthenticated):
    """Permite acesso a membros dos grupos 'suporte' ou 'admin'."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser
            or request.user.groups.filter(name__in=["admin", "suporte"]).exists()
        )


# ---------------------------------------------------------------------------
# Locais
# ---------------------------------------------------------------------------

class LocalViewSet(viewsets.ModelViewSet):
    queryset = Local.objects.select_related("pai").all()
    serializer_class = LocalSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        tipo = self.request.query_params.get("tipo")
        if q:
            qs = qs.filter(nome__icontains=q) | qs.filter(codigo__icontains=q)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs


# ---------------------------------------------------------------------------
# Ativos
# ---------------------------------------------------------------------------

class AtivoViewSet(viewsets.ModelViewSet):
    queryset = Ativo.objects.select_related("local").all()
    serializer_class = AtivoSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        categoria = self.request.query_params.get("categoria")
        estado = self.request.query_params.get("estado")
        local_id = self.request.query_params.get("local_id")
        if q:
            qs = qs.filter(modelo__icontains=q) | qs.filter(patrimonio__icontains=q)
        if categoria:
            qs = qs.filter(categoria=categoria)
        if estado:
            qs = qs.filter(estado=estado)
        if local_id:
            qs = qs.filter(local_id=local_id)
        return qs


# ---------------------------------------------------------------------------
# Itens de Estoque
# ---------------------------------------------------------------------------

class ItemEstoqueViewSet(viewsets.ModelViewSet):
    queryset = ItemEstoque.objects.all()
    serializer_class = ItemEstoqueSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        abaixo_minimo = self.request.query_params.get("abaixo_minimo")
        if q:
            qs = qs.filter(nome__icontains=q) | qs.filter(sku__icontains=q)
        if abaixo_minimo == "true":
            # filtra itens cujo qtde < nivel_minimo usando expressão no banco
            from django.db.models import F
            qs = qs.filter(qtde__lt=F("nivel_minimo"))
        return qs


# ---------------------------------------------------------------------------
# Chamados
# ---------------------------------------------------------------------------

class ChamadoViewSet(viewsets.ModelViewSet):
    queryset = Chamado.objects.select_related("ativo", "aberto_por", "agente").prefetch_related("historico").all()
    serializer_class = ChamadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        status_filter = self.request.query_params.get("status")
        prioridade = self.request.query_params.get("prioridade")
        origem = self.request.query_params.get("origem")
        q = self.request.query_params.get("q")

        # Colaboradores só veem os próprios chamados
        is_admin_or_suporte = user.is_superuser or user.groups.filter(name__in=["admin", "suporte"]).exists()
        if not is_admin_or_suporte:
            qs = qs.filter(aberto_por=user)

        if status_filter:
            qs = qs.filter(status=status_filter)
        if prioridade:
            qs = qs.filter(prioridade=prioridade)
        if origem:
            qs = qs.filter(origem=origem)
        if q:
            qs = qs.filter(assunto__icontains=q)
        return qs

    def perform_create(self, serializer):
        serializer.save(aberto_por=self.request.user)

    @action(detail=True, methods=["post"], url_path="responder", permission_classes=[IsSupporteOrAdmin])
    def responder(self, request, pk=None):
        """Adiciona um comentário ao histórico e atualiza o status do chamado."""
        chamado = self.get_object()
        novo_status = request.data.get("novo_status")
        comentario = request.data.get("comentario", "").strip()

        status_validos = [s[0] for s in Chamado.STATUS]
        if novo_status and novo_status not in status_validos:
            return Response({"detail": "Status inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if novo_status:
            chamado.status = novo_status
            if novo_status in ("resolvido", "fechado") and not chamado.fechado_em:
                chamado.fechado_em = timezone.now()
            chamado.save()

        if comentario:
            HistoricoChamado.objects.create(
                chamado=chamado,
                autor=request.user,
                texto=comentario,
            )

        serializer = self.get_serializer(chamado)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Projetos
# ---------------------------------------------------------------------------

class ProjetoViewSet(viewsets.ModelViewSet):
    queryset = Projeto.objects.select_related("responsavel").all()
    serializer_class = ProjetoSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        status_filter = self.request.query_params.get("status")
        area = self.request.query_params.get("area")
        if q:
            qs = qs.filter(titulo__icontains=q)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if area:
            qs = qs.filter(area=area)
        return qs


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups").all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        grupo = self.request.query_params.get("grupo")
        ativo = self.request.query_params.get("ativo")
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
        if grupo:
            qs = qs.filter(groups__name=grupo)
        if ativo is not None:
            qs = qs.filter(is_active=(ativo.lower() == "true"))
        return qs

    @action(detail=True, methods=["post"], url_path="definir-grupo")
    def definir_grupo(self, request, pk=None):
        """Substitui todos os grupos do usuário pelo grupo informado."""
        user = self.get_object()
        nome_grupo = request.data.get("grupo", "").strip()
        if not nome_grupo:
            return Response({"detail": "Campo 'grupo' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        grupo, _ = Group.objects.get_or_create(name=nome_grupo)
        user.groups.set([grupo])
        return Response({"detail": f"Grupo '{nome_grupo}' atribuído com sucesso."})
