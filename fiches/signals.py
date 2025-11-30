from django.db.models.signals import post_save
from django.dispatch import receiver
from fiches.models import Agent, Utilisateur

@receiver(post_save, sender=Agent)
def creer_utilisateur_pour_agent(sender, instance, created, **kwargs):
    """ Création automatique d'un utilisateur dès qu'un agent est ajouté """
    if created and not instance.utilisateur:
        utilisateur = Utilisateur.objects.create_user(
            username=instance.matricule,  # Matricule comme identifiant
            password="ANStat@123",  # Mot de passe par défaut
            role="agent"
        )
        instance.utilisateur = utilisateur  # Lie l'utilisateur à l'agent
        instance.save()  # Sauvegarde définitive

# fiches/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Evaluation, EvaluationStats
from .services.evaluation_stats import compute_stats_for

@receiver(post_save, sender=Evaluation)
def keep_stats_in_sync(sender, instance, **kwargs):
    vals = compute_stats_for(instance)
    EvaluationStats.objects.update_or_create(
        evaluation=instance,
        defaults=vals,
    )

@receiver(post_delete, sender=Evaluation)
def delete_stats(sender, instance, **kwargs):
    EvaluationStats.objects.filter(evaluation_id=instance.id).delete()
