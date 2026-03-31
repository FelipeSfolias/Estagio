from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

def tier_required(*tiers):
    """
    Restringe o acesso a usuários que pertençam a pelo menos um dos tiers informados.
    Tiers são nomes de grupos (case-insensitive). superuser sempre tem acesso.
    Ex.: @tier_required("colaborador", "suporte", "admin")
    """
    allowed = {t.lower() for t in tiers}

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:  # admin total
                return view_func(request, *args, **kwargs)

            user_tiers = {g.name.lower() for g in request.user.groups.all()}
            if user_tiers & allowed:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Sem permissão para acessar esta página.")
        return _wrapped
    return decorator
