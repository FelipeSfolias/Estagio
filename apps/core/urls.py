from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pos-login/", views.pos_login_redirect, name="pos_login"),
    # Cadastros
    path("cadastros/usuarios/", views.cad_usuarios, name="cad_usuarios"),
    path("cadastros/usuarios/<int:uid>/editar/", views.usuario_editar, name="usuario_editar"),
    path("cadastros/usuarios/<int:uid>/excluir/", views.usuario_excluir, name="usuario_excluir"),
    path("cadastros/locais/", views.cad_locais, name="cad_locais"),
    path("cadastros/locais/<int:lid>/editar/", views.local_editar, name="local_editar"),
    path("cadastros/locais/<int:lid>/excluir/", views.local_excluir, name="local_excluir"),
    path("cadastros/ativos/", views.cad_ativos, name="cad_ativos"),
    path("cadastros/ativos/<int:aid>/editar/", views.ativo_editar, name="ativo_editar"),
    path("cadastros/ativos/<int:aid>/excluir/", views.ativo_excluir, name="ativo_excluir"),
    path("cadastros/itens-estoque/", views.cad_itens_estoque, name="cad_itens_estoque"),
    path("cadastros/itens/<int:iid>/editar/", views.item_editar, name="item_editar"),
    path("cadastros/itens/<int:iid>/excluir/", views.item_excluir, name="item_excluir"),
    # Patrimônios
    path("patrimonios/", views.patrimonios_lista, name="patrimonios_lista"),
    # Chamados
    path("chamados/novo/", views.chamado_novo, name="chamado_novo"),
    path("chamados/indicadores/", views.chamados_indicadores, name="chamados_indicadores"),
    path("chamados/abrir-tier/", views.chamado_criar_tier, name="chamado_criar_tier"),
    path("chamados/meus/", views.meus_chamados, name="meus_chamados"),
    path("chamados/<int:cid>/", views.chamado_detalhe, name="chamado_detalhe"),
    # Projetos
    path("projetos/kanban/", views.projetos_kanban, name="projetos_kanban"),
    path("projetos/indicadores/", views.projetos_indicadores, name="projetos_indicadores"),
    path("projetos/card/<int:pk>/", views.card_editar, name="card_editar"),
    # Assistente
    path("assistente/", views.assistente, name="assistente_chat"),
]
