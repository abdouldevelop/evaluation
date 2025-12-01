from django.contrib.auth.views import LogoutView
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import tableau_de_bord, dashboard_directeur, ajouter_evaluation, fiche_evaluation, generate_pdf, \
    modifier_evaluation, liste_evaluations, dashboard_agent, CustomLoginView, gestion_rh, dashboard_rh, \
    details_evaluation, modifier_mot_de_passe, redirection_apres_login, ajouter_agent, evaluer_responsable, \
    evaluer_agent, generer_fiche_evaluation_pdf, signer_evaluation, ajouter_avis_agent, \
    donner_decision_finale, dashboard_dg, voir_mes_notes_evaluation, telecharger_template_csv
from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView
from . import views
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='fiches/login.html'), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', tableau_de_bord, name='dashboard'),  # Page après connexion
    path('dashboard-directeur/', dashboard_directeur, name='dashboard_directeur'),
    #path('ajouter-evaluation/', ajouter_evaluation, name='ajouter_evaluation'),
    path('evaluation/<int:evaluation_id>/', fiche_evaluation, name='fiche_evaluation'),
    path('evaluation/<int:evaluation_id>/pdf/', generate_pdf, name='generate_pdf'),
    path('modifier-evaluation/<int:evaluation_id>/', modifier_evaluation, name='modifier_evaluation'),
    path('evaluations/', liste_evaluations, name='liste_evaluations'),
    path('dashboard-agent/', dashboard_agent, name='dashboard_agent'),
    path('dashboard-dg/', dashboard_dg, name='dashboard_dg'),
    path('login/', CustomLoginView.as_view(), name='login'),  # Assurer que la connexion est bien définie
    path('logout/', LogoutView.as_view(), name='logout'),  # ✅ Définition correcte de la déconnexion
    path('ajouter-evaluation/<int:agent_id>/', ajouter_evaluation, name='ajouter_evaluation'),
    path('gestionrh/', gestion_rh, name='gestion_rh'),
    path('gestionrh/telecharger-template-csv/', telecharger_template_csv, name='telecharger_template_csv'),
    path('dashboard-rh/', dashboard_rh, name='dashboard_rh'),
    #path('evaluation/<int:evaluation_id>/', details_evaluation, name='details_evaluation'),
    path("modifier-mot-de-passe/", modifier_mot_de_passe, name="modifier_mot_de_passe"),
    path('redirect/', redirection_apres_login, name='redirect_login'),
    #path('telecharger-pdf/<int:evaluation_id>/', telecharger_pdf, name='telecharger_pdf'),
    path('ajouter-agent/', ajouter_agent, name='ajouter_agent'),
    #path('telecharger-fiche-word/<int:evaluation_id>/', telecharger_fiche_word, name='telecharger_fiche_word'),
    path('details_evaluation/<int:evaluation_id>/', details_evaluation, name='details_evaluation'),
    path('voir_mes_notes/<int:evaluation_id>/', voir_mes_notes_evaluation, name='voir_mes_notes_evaluation'),
    #path('telecharger-fiche-pdf/<int:evaluation_id>/', telecharger_fiche_pdf, name='telecharger_fiche_pdf'),
    path('dashboard_directeur/', dashboard_directeur, name='dashboard_directeur'),
    path('evaluer_agent/<int:agent_id>/', evaluer_agent, name='evaluer_agent'),
    path('evaluer_responsable/<int:agent_id>/', evaluer_responsable, name='evaluer_responsable'),
    path('generer_fiche_evaluation_pdf/<int:evaluation_id>/', generer_fiche_evaluation_pdf, name='generer_fiche_evaluation_pdf'),
    path('evaluation/<int:evaluation_id>/signer/', signer_evaluation, name='signer_evaluation'),
    #path('profil-directeur/', modifier_profil_directeur, name='modifier_profil_directeur'),
    path('evaluation/<int:evaluation_id>/avis-agent/', ajouter_avis_agent, name='ajouter_avis_agent'),
    path('donner_decision_finale/<int:id>/', donner_decision_finale, name='donner_decision_finale'),
    path('evaluation/<int:evaluation_id>/signer/agent/', views.signer_evaluation_agent, name='signer_evaluation_agent'),
    path('evaluation/<int:evaluation_id>/signer/directeur/', views.signer_evaluation_directeur, name='signer_evaluation_directeur'),
    path('profil/signature/', views.gerer_signature_utilisateur, name='gerer_signature'),
    path('post-login-redirect/', redirection_apres_login, name='post_login_redirect'),
# urls.py
    path('profil/modifier/', views.modifier_profil_directeur, name='modifier_profil_directeur'),
    path('periodes/', views.gerer_periodes, name='gerer_periodes'),
    #path('periodes/<int:pk>/', views.gerer_periodes, name='modifier_periode'),
    path('dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('chart-agents/', views.chart_agents, name='chart_agents'),
    path('chart-evalues/', views.chart_evalues, name='chart_evalues'),
    path('dashboard/sous-directeur/', views.dashboard_sous_directeur, name='dashboard_sous_directeur'),
    path('evaluer/sous-directeur/<int:agent_id>/', views.evaluer_agent_sous_directeur, name='evaluer_agent_sous_directeur'),
    path('dashboard/chef-service/', views.dashboard_chef_service, name='dashboard_chef_service'),
    path('evaluer/chef-service/<int:agent_id>/', views.evaluer_agent_chef_service, name='evaluer_agent_chef_service'),
    path('evaluer_responsable_sous_directeur/<int:agent_id>/', views.evaluer_responsable_sous_directeur, name='evaluer_responsable_sous_directeur'),
    #path('evaluer-directeur/<int:directeur_id>/', views.evaluer_directeur, name='evaluer_directeur'),
    path("evaluer_directeur/<int:agent_id>/", views.evaluer_directeur, name="evaluer_directeur"),
    #path('evaluer_directeur/<int:directeur_id>/', views.evaluer_directeur, name='evaluer_directeur')
    path('modifier-evaluation-responsable/<int:evaluation_id>/', modifier_evaluation, name='modifier_evaluation_responsable'),
    path("signer_evaluation_dg/<int:evaluation_id>/", views.signer_evaluation_dg, name="signer_evaluation_dg"),
    path("periodes/", views.gerer_periodes, name="gerer_periodes"),                 # liste seule
    path("periodes/nouveau/", views.ajouter_periode, name="ajouter_periode"),       # page d'ajout
    path("periodes/<int:pk>/modifier/", views.modifier_periode, name="modifier_periode"),



]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)