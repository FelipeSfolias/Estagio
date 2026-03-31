from rest_framework.routers import DefaultRouter

from .api_views import (
    AtivoViewSet,
    ChamadoViewSet,
    ItemEstoqueViewSet,
    LocalViewSet,
    ProjetoViewSet,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register("locais", LocalViewSet, basename="local")
router.register("ativos", AtivoViewSet, basename="ativo")
router.register("itens-estoque", ItemEstoqueViewSet, basename="itemestoque")
router.register("chamados", ChamadoViewSet, basename="chamado")
router.register("projetos", ProjetoViewSet, basename="projeto")
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = router.urls
