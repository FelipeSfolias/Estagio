from django.db import models
from django.contrib.auth.models import User


class Local(models.Model):
    TIPOS = [
        ("Site", "Site"),
        ("Prédio", "Prédio"),
        ("Andar", "Andar"),
        ("Sala", "Sala"),
        ("Rack", "Rack"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=30, choices=TIPOS)
    pai = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="filhos",
    )

    class Meta:
        verbose_name = "Local"
        verbose_name_plural = "Locais"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} – {self.nome}"


class Ativo(models.Model):
    CATEGORIAS = [
        ("Notebook", "Notebook"),
        ("Desktop", "Desktop"),
        ("Monitor", "Monitor"),
        ("Nobreak", "Nobreak"),
        ("Smartphone", "Smartphone"),
        ("Servidor", "Servidor"),
        ("Impressora", "Impressora"),
        ("Switch", "Switch"),
        ("Outro", "Outro"),
    ]
    ESTADOS = [
        ("em_uso", "Em Uso"),
        ("estoque", "Estoque"),
        ("manutencao", "Manutenção"),
        ("descartado", "Descartado"),
    ]

    patrimonio = models.CharField(max_length=20, unique=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100)
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="estoque")
    local = models.ForeignKey(
        Local,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ativos",
    )
    custodiante = models.CharField(max_length=150, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ativo"
        verbose_name_plural = "Ativos"
        ordering = ["patrimonio"]

    def __str__(self):
        return f"{self.patrimonio} – {self.modelo}"


class ItemEstoque(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    nome = models.CharField(max_length=150)
    unidade = models.CharField(max_length=20, default="pc")
    nivel_minimo = models.PositiveIntegerField(default=0)
    qtde = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Item de Estoque"
        verbose_name_plural = "Itens de Estoque"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.sku} – {self.nome}"

    @property
    def abaixo_minimo(self):
        return self.qtde < self.nivel_minimo


class Chamado(models.Model):
    ORIGENS = [
        ("Infra", "Infra"),
        ("Suporte", "Suporte"),
        ("ERP", "ERP"),
        ("Sistemas Internos", "Sistemas Internos"),
        ("BI", "BI"),
        ("Compras", "Compras"),
        ("Manutenção", "Manutenção"),
    ]
    PRIORIDADES = [
        ("baixa", "Baixa"),
        ("média", "Média"),
        ("alta", "Alta"),
    ]
    STATUS = [
        ("aberto", "Aberto"),
        ("em_atendimento", "Em Atendimento"),
        ("resolvido", "Resolvido"),
        ("fechado", "Fechado"),
    ]

    assunto = models.CharField(max_length=120)
    descricao = models.TextField()
    origem = models.CharField(max_length=30, choices=ORIGENS)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADES, default="média")
    status = models.CharField(max_length=20, choices=STATUS, default="aberto")
    aberto_em = models.DateTimeField(auto_now_add=True)
    fechado_em = models.DateTimeField(null=True, blank=True)
    sla_horas = models.PositiveIntegerField(default=8)
    ativo = models.ForeignKey(
        Ativo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chamados",
    )
    aberto_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chamados_abertos",
    )
    agente = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chamados_atribuidos",
    )

    class Meta:
        verbose_name = "Chamado"
        verbose_name_plural = "Chamados"
        ordering = ["-aberto_em"]

    def __str__(self):
        return f"#{self.pk} – {self.assunto} [{self.status}]"


class HistoricoChamado(models.Model):
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="historico",
    )
    autor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    texto = models.TextField()
    quando = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de Chamado"
        verbose_name_plural = "Históricos de Chamados"
        ordering = ["quando"]

    def __str__(self):
        return f"Chamado #{self.chamado_id} – {self.quando:%d/%m/%Y %H:%M}"


class Projeto(models.Model):
    AREAS = [
        ("Infraestrutura de T.I", "Infraestrutura de T.I"),
        ("Administrativo", "Administrativo"),
        ("Comercial", "Comercial"),
        ("Controle Industrial", "Controle Industrial"),
    ]
    STATUS = [
        ("nao_iniciado", "Não Iniciado"),
        ("em_andamento", "Em Andamento"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]

    titulo = models.CharField(max_length=200)
    responsavel = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projetos",
    )
    status = models.CharField(max_length=20, choices=STATUS, default="nao_iniciado")
    area = models.CharField(max_length=50, choices=AREAS)
    percentual = models.FloatField(default=0.0)
    prazo = models.DateField()
    atrasado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["prazo"]

    def __str__(self):
        return f"{self.titulo} [{self.status}]"
