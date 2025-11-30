from django import template

register = template.Library()

@register.filter
def get_dashboard_url(user):
    if user.is_directeur_general:
        return 'dashboard_directeur_general'
    if user.is_directeur:
        return 'dashboard_directeur'
    if user.is_sous_directeur:
        return 'dashboard_sous_directeur'
    if user.is_chef_service:
        return 'dashboard_chef_service'
    if user.is_agent:
        return 'dashboard_agent'
    return 'login'
