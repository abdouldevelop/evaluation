from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

# fiches/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def hash(dictionary, key):
    return dictionary.get(key, {})

# fiches/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    """Récupère mapping[key] ou '' si absent."""
    try:
        return mapping.get(key, '')
    except Exception:
        return ''

@register.filter
def get_field(form, name):
    """Récupère form[name] (un BoundField)."""
    try:
        return form[name]
    except Exception:
        return None

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Récupère dictionary[key] ou None si absent."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    return d.get(key)

@register.filter
def get_field(form, name):
    """Récupère le champ du form par son nom dynamique."""
    return form[name]


from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    """
    Accès sécurisé à une clé/index/attribut :
    - dict -> d.get(key)
    - list/tuple -> index si key est un entier
    - objet -> getattr(obj, key, None)
    - None -> None
    """
    if mapping is None:
        return None

    # dictionnaire
    if isinstance(mapping, dict):
        return mapping.get(key)

    # liste/tuple
    if isinstance(mapping, (list, tuple)):
        try:
            idx = int(key)
        except (TypeError, ValueError):
            return None
        return mapping[idx] if 0 <= idx < len(mapping) else None

    # objet (fallback)
    try:
        return getattr(mapping, key)
    except Exception:
        return None


# fiches/templatetags/dict_extras.py
from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    try:
        if d is None:
            return None
        return d.get(key) if hasattr(d, 'get') else d[key]
    except Exception:
        return None

