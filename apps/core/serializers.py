from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Ativo, Chamado, HistoricoChamado, ItemEstoque, Local, Projeto


class LocalSerializer(serializers.ModelSerializer):
    pai_nome = serializers.CharField(source="pai.nome", read_only=True)

    class Meta:
        model = Local
        fields = ["id", "codigo", "nome", "tipo", "pai", "pai_nome"]


class AtivoSerializer(serializers.ModelSerializer):
    local_nome = serializers.CharField(source="local.nome", read_only=True)

    class Meta:
        model = Ativo
        fields = [
            "id",
            "patrimonio",
            "numero_serie",
            "modelo",
            "categoria",
            "estado",
            "local",
            "local_nome",
            "custodiante",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["criado_em", "atualizado_em"]


class ItemEstoqueSerializer(serializers.ModelSerializer):
    abaixo_minimo = serializers.BooleanField(read_only=True)

    class Meta:
        model = ItemEstoque
        fields = ["id", "sku", "nome", "unidade", "nivel_minimo", "qtde", "abaixo_minimo"]


class HistoricoChamadoSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source="autor.get_full_name", read_only=True)

    class Meta:
        model = HistoricoChamado
        fields = ["id", "autor", "autor_nome", "texto", "quando"]
        read_only_fields = ["quando"]


class ChamadoSerializer(serializers.ModelSerializer):
    historico = HistoricoChamadoSerializer(many=True, read_only=True)
    aberto_por_nome = serializers.CharField(source="aberto_por.get_full_name", read_only=True)
    agente_nome = serializers.CharField(source="agente.get_full_name", read_only=True)
    ativo_patrimonio = serializers.CharField(source="ativo.patrimonio", read_only=True)

    class Meta:
        model = Chamado
        fields = [
            "id",
            "assunto",
            "descricao",
            "origem",
            "prioridade",
            "status",
            "aberto_em",
            "fechado_em",
            "sla_horas",
            "ativo",
            "ativo_patrimonio",
            "aberto_por",
            "aberto_por_nome",
            "agente",
            "agente_nome",
            "historico",
        ]
        read_only_fields = ["aberto_em"]


class ProjetoSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source="responsavel.get_full_name", read_only=True)

    class Meta:
        model = Projeto
        fields = [
            "id",
            "titulo",
            "responsavel",
            "responsavel_nome",
            "status",
            "area",
            "percentual",
            "prazo",
            "atrasado",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["criado_em", "atualizado_em"]


class UsuarioSerializer(serializers.ModelSerializer):
    grupos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_active", "grupos"]

    def get_grupos(self, obj):
        return list(obj.groups.values_list("name", flat=True))
