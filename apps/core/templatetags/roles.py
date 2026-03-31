from django import template

register = template.Library()

@register.filter
def has_group(user, group_name: str) -> bool:
    """
    Uso no template: {% if user|has_group:'suporte' %} ...
    Case-insensitive. Retorna False se não estiver autenticado.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name__iexact=group_name).exists()
# frontend/templatetags/roles.py
from django import template
register = template.Library()

@register.filter
def has_group(user, name):
    try:
        return user.groups.filter(name__iexact=name).exists()
    except Exception:
        return False
