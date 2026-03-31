# frontend/context_processors.py
def user_tiers(request):
    user = request.user
    tiers = set()
    if user.is_authenticated:
        tiers = {g.name.lower() for g in user.groups.all()}
    return {
        "is_admin":    user.is_authenticated and (user.is_superuser or "admin" in tiers),
        "is_suporte":  user.is_authenticated and (user.is_superuser or "suporte" in tiers),
        "is_colab":    user.is_authenticated and ("colaborador" in tiers),
    }
