from django import template
register = template.Library()

@register.filter
def get_local_nome(local_id, locais):
    m = next((l for l in locais if l["id"] == local_id), None)
    return m["nome"] if m else "-"
