from django import forms

class UsuarioForm(forms.Form):
    nome = forms.CharField()
    email = forms.EmailField()
    nome_usuario = forms.CharField(label="Nome de usuário")
    role = forms.ChoiceField(choices=[("admin","admin"),("gestor","gestor"),("usuario","usuario")])
    ativo = forms.BooleanField(initial=True, required=False)

class LocalForm(forms.Form):
    codigo = forms.CharField()
    nome = forms.CharField()
    tipo = forms.CharField()
    pai_id = forms.IntegerField(required=False)

class ChamadoPublicForm(forms.Form):
    assunto = forms.CharField(label="Assunto", max_length=120)
    descricao = forms.CharField(label="Descrição", widget=forms.Textarea(attrs={"rows": 6}))
    origem = forms.ChoiceField(label="Origem", choices=[("Infra","Infra"), ("Suporte","Suporte"), ("ERP","ERP")])
    prioridade = forms.ChoiceField(label="Prioridade", choices=[("baixa","baixa"), ("média","média"), ("alta","alta")])
    ativo_id = forms.IntegerField(label="Ativo id (opcional)", required=False)
    anexo = forms.FileField(label="Anexo (opcional)", required=False)



TIPOS_ATIVO = [
    ("Notebook", "Notebook"),
    ("Desktop", "Desktop"),
    ("Monitor", "Monitor"),
    ("Nobreak", "Nobreak"),
    ("Smartphone", "Smartphone"),
]

ESTADOS = [("em_uso","em_uso"),("estoque","estoque"),("manutencao","manutencao")]

class AtivoForm(forms.Form):
    patrimonio = forms.CharField(
        label="Patrimônio",
        help_text="Informe 4 dígitos (ex.: 0007). Será salvo como PAT-0007."
    )
    numero_serie = forms.CharField(label="Número de Série")
    modelo = forms.CharField(label="Modelo")
    categoria = forms.ChoiceField(label="Categoria", choices=TIPOS_ATIVO)
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS)
    local_id = forms.IntegerField(label="Local (id)")
    custodiante = forms.CharField(label="Custodiante", required=False)


class ItemEstoqueForm(forms.Form):
    sku = forms.CharField()
    nome = forms.CharField()
    unidade = forms.CharField()
    nivel_minimo = forms.IntegerField()
    qtde = forms.IntegerField(required=False, initial=0)

class AbrirChamadoForm(forms.Form):
    assunto = forms.CharField(label="Assunto")
    descricao = forms.CharField(widget=forms.Textarea, label="Descrição")
    origem = forms.ChoiceField(label="Origem", choices=[("Infra","Infra"),("ERP","ERP"),("Sistemas Internos","Sistemas Internos"),("BI","BI"),("Compras","Compras"),("Suporte","Suporte")])
    prioridade = forms.ChoiceField(label="Prioridade", choices=[("baixa","baixa"),("média","média"),("alta","alta")])
    ativo_id = forms.IntegerField(required=False, label="Ativo id")


class ResponderChamadoForm(forms.Form):
    novo_status = forms.ChoiceField(choices=[("aberto","aberto"),("em_atendimento","em_atendimento"),("resolvido","resolvido"),("fechado","fechado")])
    comentario = forms.CharField(widget=forms.Textarea, required=False, label="Adicionar comentário")
