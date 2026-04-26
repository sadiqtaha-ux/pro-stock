# core/templatetags/app_filters.py
from django import template

register = template.Library()

@register.filter(name='filter_statut')
def filter_statut(queryset, statut):
    """Filtre un queryset ou une liste d'objets sur l'attribut calculated_statut."""
    if not queryset:
        return []
    return [obj for obj in queryset if getattr(obj, 'calculated_statut', '') == statut]

@register.filter(name='filter_attr')
def filter_attr(queryset, args):
    """
    Filtre un queryset ou une liste sur un attribut spécifique.
    Usage: {{ objects|filter_attr:'statut:ACTIF' }}
    """
    if not queryset or ':' not in args:
        return []
    attr, val = args.split(':')
    return [obj for obj in queryset if str(getattr(obj, attr, '')) == val]
@register.filter(name='subtract')
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='format_qty')
def format_qty(value):
    """
    Formate une quantité pour masquer les décimales inutiles.
    Ex: 20.0000 -> 20 | 19.5000 -> 19.5
    """
    if value is None:
        return ""
    try:
        val = float(value)
        if val == int(val):
            return f"{int(val)}"
        # Utilisation de :g pour les chiffres significatifs (max 10)
        return f"{val:g}"
    except (ValueError, TypeError):
        return value
