# fiches/templatetags/evaluation_filters.py
from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    return float(value) * float(arg)

@register.filter
def divide(value, arg):
    return float(value) / float(arg)

# fiches/templatetags/evaluation_filters.py
from django import template

register = template.Library()

@register.filter
def div(value, divisor):
    """
    Divise la valeur par le diviseur. Retourne 0 si le diviseur est 0 ou si la valeur est None.
    """
    try:
        return float(value) / float(divisor)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

# fiches/templatetags/evaluation_filters.py
from django import template

register = template.Library()

@register.filter
def attr(obj, field_name):
    """
    Permet d'accéder dynamiquement à obj.field_name dans votre template.
    Usage : {{ evaluation|attr:"connaissances" }}
    """
    return getattr(obj, field_name, '')

from django import template

register = template.Library()

@register.filter(name='div')
def div(value, arg):
    """
    Divise value par arg.
    Usage en template : {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return None


from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(mapping, key):
    """
    Récupère mapping[key] dans un dict (ou None si absent).
    Utilisation: {{ mon_dict|get_item:cle }}
    """
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None

@register.filter(name='div')
def div(value, arg):
    """
    Division sûre dans les templates.
    Utilisation: {{ valeur|div:5 }}
    Gère None et division par zéro en renvoyant None.
    """
    try:
        if value is None or arg in (None, 0, '0', '0.0'):
            return None
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return None

@register.filter(name='safe_float')
def safe_float(value, default=0.0):
    """
    Convertit en float sinon renvoie 'default' (0.0 par défaut).
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

# fiches/templatetags/evaluation_filters.py
import json
from django import template

register = template.Library()

@register.filter
def ensure_list(value):
    """
    Normalise la valeur en liste.
    - None / ''  -> []
    - list/tuple/set -> list(...)
    - str JSON list  -> liste parsée
    - str simple     -> [str]
    - autre          -> [value]
    """
    if value in (None, '', 'None'):
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith('[') and s.endswith(']'):
            try:
                data = json.loads(s)
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return [value]
    return [value]


# fiches/templatetags/evaluation_filters.py
from django import template

register = template.Library()



from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def div(value, arg):
    try:
        v = float(value)
        a = float(arg)
        return v / a if a else 0
    except (TypeError, ValueError):
        return 0