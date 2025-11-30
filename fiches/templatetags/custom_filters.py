"""from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):  # ✅ Vérifie que c'est bien un dictionnaire
        return dictionary.get(key)
    return None  # ✅ Retourne None si ce n'est pas un dictionnaire"""

# fiches/templatetags/evaluation_filters.py

from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplie deux valeurs numériques."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def dict_key(d, key):
    return d.get(key, None)

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

# fiches/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def semestre_display(value):
    if value == 1:
        return "1er Semestre"
    elif value == 2:
        return "2ème Semestre"
    return str(value)
