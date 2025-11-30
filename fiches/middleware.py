from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class ForceChangeDefaultPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        # on ne s'applique qu'aux agents encore sur mot de passe par défaut
        if (
            user.is_authenticated
            and getattr(user, 'role', None) == 'agent'
            and user.check_password(settings.DEFAULT_PASSWORD)
        ):
            allowed = [
                reverse('modifier_mot_de_passe'),
                reverse('logout'),
                reverse('login'),
            ]
            if request.path not in allowed:
                return redirect('modifier_mot_de_passe')

        return self.get_response(request)
