from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class ForceChangeDefaultPasswordMiddleware:
    """
    Middleware qui force TOUS les utilisateurs ayant le mot de passe par défaut
    à le changer lors de leur première connexion avant d'accéder au système.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        # S'applique à TOUS les utilisateurs authentifiés qui ont encore le mot de passe par défaut
        if (
            user.is_authenticated
            and user.check_password(settings.DEFAULT_PASSWORD)
        ):
            # Pages autorisées même avec le mot de passe par défaut
            allowed = [
                reverse('modifier_mot_de_passe'),
                reverse('logout'),
                reverse('login'),
            ]
            # Autoriser aussi les fichiers statiques et media
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                return self.get_response(request)

            # Si l'utilisateur essaie d'accéder à une autre page, redirection forcée
            if request.path not in allowed:
                return redirect('modifier_mot_de_passe')

        return self.get_response(request)
