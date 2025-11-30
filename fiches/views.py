from django.core.checks import messages
from django.contrib.auth.decorators import login_required
@login_required
def liste_evaluations(request):
    user = request.user

    if user.is_rh() or user.is_directeur_general():
        evaluations = Evaluation.objects.all()  # RH et Directeur Général voient tout
    elif user.is_directeur():
        evaluations = Evaluation.objects.filter(agent__direction=user.direction)  # Directeur voit sa direction
    else:
        evaluations = Evaluation.objects.filter(agent=user)  # Un agent ne voit que sa propre évaluation

    return render(request, 'fiches/liste_evaluations.html', {'evaluations': evaluations})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from fiches.models import Evaluation, Agent, UserProfile, SousDirection
from fiches.forms import EvaluationForm
from django.contrib import messages
from datetime import datetime

@login_required
def ajouter_evaluation(request, agent_id):
    """ Permet au directeur d'évaluer un agent """
    agent = get_object_or_404(Agent, id=agent_id)
    evaluation, created = Evaluation.objects.get_or_create(
        agent=agent, annee=datetime.now().year, semestre=1
    )

    if request.user.is_directeur() and agent.direction.directeur != request.user:
        return render(request, 'fiches/erreur.html', {'message': "Vous ne pouvez pas évaluer cet agent."})

    if request.method == "POST":
        print("📩 Données reçues :", request.POST)  # ✅ Debug : Voir les données envoyées

        form = EvaluationForm(request.POST,instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)  # ✅ Ne sauvegarde pas immédiatement
            evaluation.type_personnel = agent.type_personnel  # ✅ Enregistre le type de personnel
            evaluation.agent = agent
            evaluation.save()  # ✅ Enregistrement de l'évaluation

            evaluation.calcul_moyennes()  # ✅ Mise à jour des moyennes après l'enregistrement
            print(f"✅ Évaluation créée : M1={evaluation.moyenne_rendement}, M2={evaluation.moyenne_comportement}")  # ✅ Debug

            return redirect('dashboard_directeur')
        else:
            print("❌ Formulaire invalide :", form.errors)  # ✅ Debug : Voir les erreurs

    else:
        form = EvaluationForm(instance=evaluation, initial={'type_personnel': agent.type_personnel, 'annee': datetime.now().year})
        #form = EvaluationForm()

    return render(request, 'fiches/ajouter_evaluation.html', {
        'form': form,
        'agent': agent,
        'poste': getattr(agent, 'poste', 'Non défini'),  # ✅ Évite l'erreur si poste est absent
        'tenu_depuis': getattr(agent, 'tenu_depuis', 'Non défini')
    })



@login_required
def donner_avis(request, id):
    evaluation = get_object_or_404(Evaluation, id=id)

    if request.user.is_agent() and evaluation.agent != request.user:
        return redirect('liste_evaluations')  # Un agent ne peut donner son avis que sur sa propre évaluation

    if request.method == 'POST':
        evaluation.avis_agent = request.POST['avis']
        evaluation.save()
        return redirect('liste_evaluations')

    return render(request, 'fiches/donner_avis.html', {'evaluation': evaluation})

"""# fiches/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts       import get_object_or_404, redirect, render
from django.contrib        import messages
from .models               import Evaluation

@login_required
def donner_decision_finale(request, id):
    # Seul le Directeur Général peut donner la décision finale
    if not hasattr(request.user, 'is_directeur_general') or not request.user.is_directeur_general():
        return redirect('liste_evaluations')

    evaluation = get_object_or_404(Evaluation, id=id)
    errors = {}

    if request.method == 'POST':
        decision = request.POST.get('decision', '').strip()
        autres   = request.POST.get('autres', '').strip()

        # Validation
        if not decision:
            errors['decision'] = "⚠️ Veuillez sélectionner une décision."
        if decision == 'autres' and not autres:
            errors['autres'] = "⚠️ Merci de préciser la décision."

        if not errors:
            # Enregistrement
            evaluation.decision_finale   = decision
            evaluation.autres_decision   = autres if decision == 'autres' else ''
            evaluation.save()
            messages.success(request, "✅ Décision finale enregistrée.")
            return redirect('dashboard_dg')

    else:
        # Pré-remplissage
        decision = evaluation.decision_finale
        autres   = evaluation.autres_decision

    return render(request, 'fiches/donner_decision_finale.html', {
        'evaluation': evaluation,
        'decision':   decision,
        'autres':     autres,
        'errors':     errors,
    })
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.conf import settings  # si besoin
from .models import Evaluation
import json

@login_required
def donner_decision_finale(request, id):
    # Seul le DG
    if not hasattr(request.user, 'is_directeur_general') or not request.user.is_directeur_general():
        return redirect('liste_evaluations')

    evaluation = get_object_or_404(Evaluation, id=id)
    errors = {}

    # --- utilitaires de sérialisation (si ton champ n'est pas une liste native) ---
    def load_decisions(value):
        """
        Normalise la valeur stockée en liste Python.
        - Si ton modèle a un MultiSelectField/ArrayField -> value est déjà list-like.
        - Sinon on parse une chaîne CSV.
        """
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        # sinon: CSV "promotion,formation"
        return [v.strip() for v in str(value).split(',') if v.strip()]

    def dump_decisions(decisions):
        """
        Transforme la liste en format de stockage.
        - Si ton modèle accepte une liste (MultiSelectField/ArrayField) -> renvoyer la liste.
        - Si c'est un CharField -> renvoyer une chaîne CSV.
        """
        # ➜ ADAPTE ici suivant ton modèle:
        #   - si Evaluation.decision_finale est un MultiSelectField/ArrayField: return decisions
        #   - si c'est un CharField: return ",".join(decisions)
        try:
            # test simple: si l'attribut actuel est list-like, on garde une liste
            _ = iter(getattr(evaluation, 'decision_finale', []))
            if isinstance(getattr(evaluation, 'decision_finale', []), (list, tuple)):
                return decisions
        except TypeError:
            pass
        return ",".join(decisions)

    if request.method == 'POST':
        # 1) Récupération multi
        decisions = request.POST.getlist('decision_finale')  # ex: ['promotion', 'formation', 'autres']
        autres = (request.POST.get('autres') or '').strip()

        # 2) Validation
        if not decisions:
            errors['decision_finale'] = "⚠️ Veuillez sélectionner au moins une décision."
        if 'autres' in decisions and not autres:
            errors['autres'] = "⚠️ Merci de préciser la décision si vous cochez « Autres »."

        if not errors:
            # 3) Enregistrement
            evaluation.decision_finale = json.dumps(decisions, ensure_ascii=False)  # stocker en JSON
            evaluation.autres_decision = autres if 'autres' in decisions else ''
            evaluation.save()

            messages.success(request, "✅ Décision(s) finale(s) enregistrée(s).")
            return redirect('dashboard_dg')

        # Si erreurs, on retombe en GET avec les valeurs saisies
        selected = decisions
    else:
        # Pré-remplissage depuis la base
        selected = load_decisions(evaluation.decision_finale)
        autres = evaluation.autres_decision or ""

    # 4) Rendu
    return render(request, 'fiches/donner_decision_finale.html', {
        'evaluation': evaluation,
        'errors': errors,
        'selected': selected,           # utile si tu préfères tester membership sur 'selected'
        'autres': autres,
    })






from django.shortcuts import render
from .models import Evaluation

def liste_evaluations(request):
    evaluations = Evaluation.objects.all().order_by('-date_evaluation')
    return render(request, 'fiches/liste_evaluations.html', {'evaluations': evaluations})

"""
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required

from .models import Evaluation
from .forms import EvaluationForm

@login_required
def modifier_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # Blocage si signé
    if evaluation.est_signe_directeur:
        messages.warning(
            request,
            "Cette évaluation a déjà été signée par le directeur et ne peut plus être modifiée."
        )
        return redirect('dashboard_directeur')

    # Contrôle d’autorisation
    if not request.user.is_directeur() or \
       evaluation.agent.direction.directeur != request.user:
        messages.error(request, "Vous ne pouvez pas modifier cette évaluation.")
        return redirect('dashboard_directeur')

    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.calcul_moyennes()
            evaluation.save()
            messages.success(request, "Évaluation modifiée avec succès !")
            return redirect('dashboard_directeur')
    else:
        form = EvaluationForm(instance=evaluation)

    # → Créez ici le dict des justifications (même vide si vous ne les stockez pas encore)
    justifications = {
        'connaissances': getattr(evaluation, 'connaissances_justif', ''),
        'initiative': getattr(evaluation, 'initiative_justif', ''),
        'rendement': getattr(evaluation, 'rendement_justif', ''),
        'respect_objectifs': getattr(evaluation, 'respect_objectifs_justif', ''),
    }

    return render(request, 'fiches/evaluer_agent.html', {
        'form': form,
        'agent': evaluation.agent,
        'evaluation': evaluation,
        'justifications': justifications,  # <-- indispensable !
    })
"""




from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse

from .models import Evaluation, JustificationNote  # Assure-toi d'importer JustificationNote
from .forms import EvaluationForm

@login_required
def modifier_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    agent = evaluation.agent

    # 1) Blocage si signé
    if getattr(evaluation, 'est_signe_directeur', False):
        messages.warning(
            request,
            "Cette évaluation a déjà été signée par le directeur et ne peut plus être modifiée."
        )
        return redirect('dashboard_directeur')

    # 2) Contrôle d’autorisation (adapte si ton projet a d'autres règles)
    if not hasattr(request.user, 'is_directeur') or not request.user.is_directeur():
        messages.error(request, "Vous ne pouvez pas modifier cette évaluation.")
        return redirect('dashboard_directeur')
    if getattr(agent.direction, 'directeur', None) != request.user:
        messages.error(request, "Vous ne pouvez pas modifier cette évaluation (agent hors de votre direction).")
        return redirect('dashboard_directeur')

    # 3) Préparer les maps CS/SD + justifs comme dans evaluer_agent
    CS_CRITS = [f"{nom}_chef_service" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]
    SD_CRITS = [f"{nom}_sous_directeur" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]

    cs_vals = {nom: getattr(evaluation, nom, None) for nom in CS_CRITS}
    sd_vals = {nom: getattr(evaluation, nom, None) for nom in SD_CRITS}

    all_just = JustificationNote.objects.filter(evaluation=evaluation)
    cs_just = {j.critere: j.justification for j in all_just if j.critere in CS_CRITS}
    sd_just = {j.critere: j.justification for j in all_just if j.critere in SD_CRITS}
    dir_just = {
        j.critere: j.justification
        for j in all_just
        if j.critere not in CS_CRITS + SD_CRITS
    }

    # 4) Définir les critères Directeur (comme dans evaluer_agent)
    CRITS_DIR = [
        {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
        {'nom': 'initiative', 'label': "Esprit d’initiative"},
        {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
        {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
        {'nom': 'civisme', 'label': 'Civisme'},
        {'nom': 'service_public', 'label': 'Sens du service public'},
        {'nom': 'relations_humaines', 'label': 'Relations humaines'},
        {'nom': 'discipline', 'label': "Esprit de discipline"},
        {'nom': 'ponctualite', 'label': 'Ponctualité'},
        {'nom': 'assiduite', 'label': 'Assiduité'},
        {'nom': 'tenue', 'label': 'Tenue'},
    ]
    if agent.type_personnel == 'responsable':
        CRITS_DIR += [
            {'nom': 'leadership', 'label': 'Leadership'},
            {'nom': 'planification', 'label': 'Planification'},
            {'nom': 'travail_equipe', 'label': "Travail d’équipe"},
            {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
            {'nom': 'prise_decision', 'label': 'Prise de décision'},
        ]

    # 5) POST/GET
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            with transaction.atomic():
                ev = form.save(commit=False)
                # on verrouille ces champs cohérents
                ev.type_personnel = agent.type_personnel
                ev.agent = agent
                ev.annee = evaluation.annee
                ev.semestre = evaluation.semestre
                ev.save()
                ev.calcul_moyennes()

                # (Optionnel) remettre à jour les justifs du Directeur :
                # on ne touche PAS aux justifs CS/SD ici
                JustificationNote.objects.filter(
                    evaluation=ev
                ).exclude(critere__in=CS_CRITS + SD_CRITS).delete()

                # pour chaque critère directeur, si note 1/5 et texte => créer la justif
                for crit in [c['nom'] for c in CRITS_DIR]:
                    note = getattr(ev, crit, None)
                    justif = (request.POST.get(f"{crit}_justif") or "").strip()
                    if note in (1, 5) and justif:
                        JustificationNote.objects.create(
                            evaluation=ev,
                            critere=crit,
                            note=note,
                            justification=justif
                        )

            messages.success(request, "Évaluation modifiée avec succès !")
            return redirect('dashboard_directeur')
        else:
            messages.error(request, "⚠️ Formulaire invalide.")
    else:
        # initial pour cohérence avec le form (si besoin)
        initial = {'type_personnel': agent.type_personnel}
        form = EvaluationForm(instance=evaluation, initial=initial)

    # 6) Construire la liste des champs pour le template (comme evaluer_agent)
    champs = []
    for crit in CRITS_DIR:
        nom = crit['nom']
        champs.append({
            'field':   form[nom],
            'label':   crit['label'],
            'cs_note': cs_vals.get(f"{nom}_chef_service"),
            'cs_just': cs_just.get(f"{nom}_chef_service", ""),
            'sd_note': sd_vals.get(f"{nom}_sous_directeur"),
            'sd_just': sd_just.get(f"{nom}_sous_directeur", ""),
            'dir_just':dir_just.get(nom, ""),
        })

    return render(request, 'fiches/evaluer_agent.html', {
        'form':     form,
        'agent':    agent,
        'semestre': evaluation.semestre,   # requis par le template
        'champs':   champs,                # requis par le template
    })


@login_required
def modifier_evaluation_responsable(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    agent = evaluation.agent

    if getattr(evaluation, 'est_signe_directeur', False):
        messages.warning(request, "Cette évaluation a déjà été signée par le directeur et ne peut plus être modifiée.")
        return redirect('dashboard_directeur')

    if not hasattr(request.user, 'is_directeur') or not request.user.is_directeur():
        messages.error(request, "Vous ne pouvez pas modifier cette évaluation.")
        return redirect('dashboard_directeur')
    if getattr(agent.direction, 'directeur', None) != request.user:
        messages.error(request, "Vous ne pouvez pas modifier cette évaluation (agent hors de votre direction).")
        return redirect('dashboard_directeur')

    CS_CRITS = [f"{nom}_chef_service" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]
    SD_CRITS = [f"{nom}_sous_directeur" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]

    cs_vals = {nom: getattr(evaluation, nom, None) for nom in CS_CRITS}
    sd_vals = {nom: getattr(evaluation, nom, None) for nom in SD_CRITS}

    all_just = JustificationNote.objects.filter(evaluation=evaluation)
    cs_just = {j.critere: j.justification for j in all_just if j.critere in CS_CRITS}
    sd_just = {j.critere: j.justification for j in all_just if j.critere in SD_CRITS}
    dir_just = { j.critere: j.justification
                 for j in all_just
                 if j.critere not in CS_CRITS + SD_CRITS }

    CRITS_DIR = [
        {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
        {'nom': 'initiative', 'label': "Esprit d’initiative"},
        {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
        {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
        {'nom': 'civisme', 'label': 'Civisme'},
        {'nom': 'service_public', 'label': 'Sens du service public'},
        {'nom': 'relations_humaines', 'label': 'Relations humaines'},
        {'nom': 'discipline', 'label': "Esprit de discipline"},
        {'nom': 'ponctualite', 'label': 'Ponctualité'},
        {'nom': 'assiduite', 'label': 'Assiduité'},
        {'nom': 'tenue', 'label': 'Tenue'},
        {'nom': 'leadership', 'label': 'Leadership'},
        {'nom': 'planification', 'label': 'Planification'},
        {'nom': 'travail_equipe', 'label': "Travail d’équipe"},
        {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
        {'nom': 'prise_decision', 'label': 'Prise de décision'},
    ]

    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            with transaction.atomic():
                ev = form.save(commit=False)
                ev.type_personnel = agent.type_personnel
                ev.agent = agent
                ev.annee = evaluation.annee
                ev.semestre = evaluation.semestre
                ev.save()
                ev.calcul_moyennes()

                JustificationNote.objects.filter(evaluation=ev)\
                    .exclude(critere__in= SD_CRITS).delete()

                for crit in [c['nom'] for c in CRITS_DIR]:
                    note = getattr(ev, crit, None)
                    justif = (request.POST.get(f"{crit}_justif") or "").strip()
                    if note in (1, 5) and justif:
                        JustificationNote.objects.create(
                            evaluation=ev, critere=crit, note=note, justification=justif
                        )

            messages.success(request, "Évaluation modifiée avec succès !")
            return redirect('dashboard_directeur')
        else:
            messages.error(request, "⚠️ Formulaire invalide.")
    else:
        initial = {'type_personnel': agent.type_personnel}
        form = EvaluationForm(instance=evaluation, initial=initial)
        if 'type_personnel' in form.fields:
            from django import forms
            form.fields['type_personnel'].widget = forms.HiddenInput()

    champs = []
    for crit in CRITS_DIR:
        nom = crit['nom']
        champs.append({
            'field':   form[nom],
            'label':   crit['label'],
            'sd_note': sd_vals.get(f"{nom}_sous_directeur"),
            'sd_just': sd_just.get(f"{nom}_sous_directeur", ""),
            'dir_just':dir_just.get(nom, ""),
        })

    return render(request, 'fiches/evaluer_responsable.html', {
        'form':     form,
        'agent':    agent,
        'semestre': evaluation.semestre,
        'champs':   champs,
    })




def supprimer_evaluation(request, id):
    evaluation = get_object_or_404(Evaluation, id=id)
    if request.method == 'POST':
        evaluation.delete()
        return redirect('liste_evaluations')
    return render(request, 'fiches/supprimer_evaluation.html', {'evaluation': evaluation})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def tableau_de_bord(request):
    user = request.user

    # Redirection selon le rôle de l'utilisateur
    if user.is_agent():
        return render(request, 'fiches/dashboard_agent.html', {'user': user})
    elif user.is_directeur():
        return render(request, 'fiches/dashboard_directeur.html', {'user': user})
    elif user.is_directeur_general():
        return render(request, 'fiches/dashboard_dg.html', {'user': user})
    elif user.is_rh():
        return render(request, 'fiches/dashboard_rh.html', {'user': user})
    else:
        return redirect('login')  # Redirige vers la connexion en cas d'erreur


from django.contrib.auth.decorators import login_required

@login_required
def fiche_evaluation(request, evaluation_id):
    """ Affiche la fiche d'évaluation détaillée d'un agent """
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    evaluation = Evaluation.objects.filter(agent__utilisateur=request.user).first()
    return render(request, 'fiches/fiche_evaluation_pdf.html', {
        'evaluation': evaluation
    })


from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa
import os

@login_required
def generate_pdf(request, evaluation_id):
    """ Génère un PDF de la fiche d'évaluation d'un agent """
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # ✅ Définition du template PDF
    template_path = 'fiches/pdf_template.html'
    context = {'evaluation': evaluation}

    # ✅ Rendre le template en HTML
    template = get_template(template_path)
    html = template.render(context)

    # ✅ Configurer la réponse HTTP pour un fichier PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Evaluation_{evaluation.agent.nom}.pdf"'

    # ✅ Générer le PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    # ✅ Vérifier s'il y a une erreur
    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)

    return response



from django.contrib.auth.views import LoginView
from .forms import LoginForm

class CustomLoginView(LoginView):
    authentication_form = LoginForm  # ✅ Formulaire qui utilise `username`
    template_name = 'fiches/login.html'

import csv
from io import TextIOWrapper
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Direction, Utilisateur, Agent
from .forms import DirectionForm, DirecteurForm, AgentForm, ChangerDirectionAgentForm

@login_required
def gestion_rh(request):
    """ Page de gestion RH : directions, directeurs et agents """

    if not request.user.is_rh():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas RH."})

    directions = Direction.objects.all()
    agents = Agent.objects.select_related('direction')

    if request.method == "POST":
        if "ajouter_direction" in request.POST:
            direction_form = DirectionForm(request.POST)
            if direction_form.is_valid():
                direction_form.save()
                return redirect('gestion_rh')

        elif "ajouter_directeur" in request.POST:
            directeur_form = DirecteurForm(request.POST)
            if directeur_form.is_valid():
                directeur = directeur_form.save(commit=False)
                directeur.role = "directeur"
                directeur.set_password("ANStat@123")  # Mot de passe par défaut
                directeur.save()
                return redirect('gestion_rh')

        elif "ajouter_agent" in request.POST:
            agent_form = AgentForm(request.POST)
            if agent_form.is_valid():
                agent_form.save()
                return redirect('gestion_rh')

        elif "changer_direction" in request.POST:
            agent_id = request.POST.get("agent_id")
            agent = Agent.objects.get(id=agent_id)
            changer_direction_form = ChangerDirectionAgentForm(request.POST, instance=agent)
            if changer_direction_form.is_valid():
                changer_direction_form.save()
                return redirect('gestion_rh')

        elif "importer_personnel" in request.POST:
            fichier = request.FILES.get("fichier_csv")
            if fichier:
                try:
                    lecteur = csv.DictReader(TextIOWrapper(fichier.file, encoding='utf-8-sig'), delimiter=';')
                    compteur = 0
                    erreurs = []

                    for i, ligne in enumerate(lecteur, start=1):
                        try:
                            matricule = ligne.get('matricule', '').strip()
                            nom = ligne.get('nom', '').strip()
                            prenoms = ligne.get('prenoms', '').strip()
                            categorie = ligne.get('categorie', '').strip()
                            direction_id = ligne.get('direction_id', '').strip()
                            sous_direction = ligne.get('sous_direction', '').strip()
                            service = ligne.get('service', '').strip()
                            poste = ligne.get('poste', '').strip()
                            type_personnel = ligne.get('type_personnel', 'agent').strip()

                            # ✅ Sécurité sur les dates
                            try:
                                date_embauche = datetime.strptime(ligne.get('date_embauche', ''), "%d/%m/%Y").date()
                            except:
                                date_embauche = None

                            try:
                                tenu_depuis = datetime.strptime(ligne.get('tenu_depuis', ''), "%d/%m/%Y").date()
                            except:
                                tenu_depuis = None

                            # ✅ Convertir direction_id float/str → int
                            direction_id = int(float(direction_id)) if direction_id else None
                            direction = Direction.objects.get(id=direction_id)

                            # ✅ Vérifier doublon utilisateur
                            if Utilisateur.objects.filter(username=matricule).exists():
                                erreurs.append(f"Ligne {i} : utilisateur déjà existant ({matricule})")
                                continue

                            utilisateur = Utilisateur.objects.create_user(
                                username=matricule,
                                password="00000000",
                                role="agent",
                                matricule=matricule
                            )

                            Agent.objects.create(
                                utilisateur=utilisateur,
                                nom=nom,
                                prenoms=prenoms,
                                matricule=matricule,
                                date_embauche=date_embauche,
                                categorie=categorie,
                                direction=direction,
                                sous_direction=sous_direction,
                                service=service,
                                poste=poste,
                                tenu_depuis=tenu_depuis,
                                type_personnel=type_personnel
                            )
                            compteur += 1

                        except Direction.DoesNotExist:
                            erreurs.append(f"Ligne {i} : direction_id invalide ({direction_id})")
                        except Exception as e:
                            erreurs.append(f"Ligne {i} : erreur {str(e)}")

                    messages.success(request, f"✅ {compteur} agents importés avec succès.")
                    if erreurs:
                        messages.warning(request, "⚠️ Certaines lignes ont échoué :\n" + "\n".join(erreurs[:5]))

                except Exception as e:
                    messages.error(request, f"❌ Erreur pendant l'import : {e}")

            return redirect('gestion_rh')


    else:
        direction_form = DirectionForm()
        directeur_form = DirecteurForm()
        agent_form = AgentForm()
        changer_direction_form = ChangerDirectionAgentForm()

    return render(request, 'fiches/gestion_rh.html', {
        'directions': directions,
        'agents': agents,
        'direction_form': direction_form,
        'directeur_form': directeur_form,
        'agent_form': agent_form,
        'changer_direction_form': changer_direction_form
    })

'''
# fiches/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Direction, Evaluation


@login_required
def dashboard_rh(request):
    if not request.user.is_rh():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas RH."})

    # Récupérer toutes les directions (puisque le RH n'a pas de direction, mais les agents oui)
    directions = Direction.objects.all()

    # Récupérer les filtres
    direction_filter = request.GET.get('direction', 'all')
    annee_filter = request.GET.get('annee', '')
    semestre_filter = request.GET.get('semestre', '')

    # Récupérer toutes les évaluations (sans restriction de direction pour le RH)
    evaluations = Evaluation.objects.all().select_related('agent', 'agent__direction')

    # Appliquer les filtres
    if direction_filter != 'all':
        evaluations = evaluations.filter(agent__direction__id=direction_filter)
    if annee_filter:
        evaluations = evaluations.filter(annee=annee_filter)
    if semestre_filter:
        evaluations = evaluations.filter(semestre=semestre_filter)

    # Convertir en liste pour tri personnalisé
    evaluations_list = list(evaluations)

    # Trier les évaluations pour l'affichage dans "Liste des Évaluations"
    evaluations_list.sort(
        key=lambda
            eval: eval.stats.moyenne_generale_annuelle if eval.semestre == 2 and eval.stats.moyenne_generale_annuelle is not None else eval.moyenne_generale,
        reverse=True
    )

    # Récupérer les années disponibles pour le filtre
    annees = Evaluation.objects.all().values_list('annee', flat=True).distinct().order_by('-annee')

    # Récupérer les semestres pour le filtre
    #semestres = Evaluation.SEMESTRE_CHOICES

    # Classement par direction (séparé par semestre)
    classements_par_direction = {}
    for direction in directions:
        # Filtrer les évaluations de cette direction
        evals = [e for e in evaluations_list if e.agent.direction == direction]

        # Séparer par semestre
        evals_s1 = [e for e in evals if e.semestre == 1]
        evals_s2 = [e for e in evals if e.semestre == 2]

        # Trier S1 par moyenne_generale
        evals_s1.sort(key=lambda e: e.moyenne_generale, reverse=True)
        # Trier S2 par moyenne_generale_annuelle (si disponible)
        evals_s2.sort(
            key=lambda
                e: e.stats.moyenne_generale_annuelle if e.stats.moyenne_generale_annuelle is not None else e.moyenne_generale,
            reverse=True
        )

        # Stocker les classements par semestre
        classements_par_direction[direction] = {
            's1': evals_s1,
            's2': evals_s2
        }

    # Classement général (séparé par semestre)
    evals_s1 = [e for e in evaluations_list if e.semestre == 1]
    evals_s2 = [e for e in evaluations_list if e.semestre == 2]

    # Trier S1 par moyenne_generale
    evals_s1.sort(key=lambda e: e.moyenne_generale, reverse=True)
    # Trier S2 par moyenne_generale_annuelle (si disponible)
    evals_s2.sort(
        key=lambda e: e.stats.moyenne_generale_annuelle  if e.stats.moyenne_generale_annuelle  is not None else e.moyenne_generale,
        reverse=True
    )

    return render(request, "fiches/dashboard_rh.html", {
        "directions": directions,  # Toutes les directions
        "evaluations": evaluations_list,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,
#        "semestres": semestres,
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": evals_s1,
        "classement_general_s2": evals_s2,
    })'''

# fiches/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Direction, Evaluation


@login_required
def dashboard_rh(request):
    if not request.user.is_rh():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas RH."})

    # Récupérer toutes les directions
    directions = Direction.objects.all()

    # Récupérer les filtres
    direction_filter = request.GET.get('direction', 'all')
    annee_filter = request.GET.get('annee', '')
    semestre_filter = request.GET.get('semestre', '')

    # Récupérer UNIQUEMENT les évaluations signées par le directeur
    evaluations = Evaluation.objects.filter(
        est_signe_directeur=True  # Filtre principal : signées par le directeur
    ).select_related('agent', 'agent__direction')

    # Appliquer les filtres supplémentaires
    if direction_filter != 'all':
        evaluations = evaluations.filter(agent__direction__id=direction_filter)
    if annee_filter:
        evaluations = evaluations.filter(annee=annee_filter)
    if semestre_filter:
        evaluations = evaluations.filter(semestre=semestre_filter)

    # Convertir en liste pour tri personnalisé
    evaluations_list = list(evaluations)

    # Fonction helper pour obtenir la clé de tri avec gestion des None
    def get_sort_key(eval):
        """Retourne une clé de tri en gérant les valeurs None"""
        if eval.semestre == 2:
            # Pour le semestre 2, privilégier la moyenne annuelle si elle existe
            if hasattr(eval, 'moyenne_generale_annuelle') and eval.moyenne_generale_annuelle:
                return eval.moyenne_generale_annuelle

        # Sinon, utiliser la moyenne générale (ou 0 si None)
        return eval.moyenne_generale if eval.moyenne_generale is not None else 0

    # Trier les évaluations pour l'affichage
    evaluations_list.sort(key=get_sort_key, reverse=True)

    # Récupérer les années disponibles pour le filtre (uniquement des évaluations signées)
    annees = Evaluation.objects.filter(
        est_signe_directeur=True
    ).values_list('annee', flat=True).distinct().order_by('-annee')

    # Classement par direction (séparé par semestre) - uniquement évaluations signées
    classements_par_direction = {}
    for direction in directions:
        # Filtrer les évaluations signées de cette direction
        evals = [e for e in evaluations_list if e.agent.direction == direction]

        # Séparer par semestre
        evals_s1 = [e for e in evals if e.semestre == 1]
        evals_s2 = [e for e in evals if e.semestre == 2]

        # Trier S1 par moyenne_generale (gérer les None)
        evals_s1.sort(
            key=lambda e: e.moyenne_generale if e.moyenne_generale is not None else 0,
            reverse=True
        )

        # Trier S2 par moyenne_generale_annuelle ou moyenne_generale (gérer les None)
        def get_s2_sort_key(e):
            if hasattr(e, 'moyenne_generale_annuelle') and e.moyenne_generale_annuelle:
                return e.moyenne_generale_annuelle
            return e.moyenne_generale if e.moyenne_generale is not None else 0

        evals_s2.sort(key=get_s2_sort_key, reverse=True)

        # Stocker les classements par semestre
        classements_par_direction[direction] = {
            's1': evals_s1,
            's2': evals_s2
        }

    # Classement général (séparé par semestre) - uniquement évaluations signées
    evals_s1 = [e for e in evaluations_list if e.semestre == 1]
    evals_s2 = [e for e in evaluations_list if e.semestre == 2]

    # Trier S1 par moyenne_generale
    evals_s1.sort(
        key=lambda e: e.moyenne_generale if e.moyenne_generale is not None else 0,
        reverse=True
    )

    # Trier S2 par moyenne_generale_annuelle
    def get_s2_general_sort_key(e):
        if hasattr(e, 'moyenne_generale_annuelle') and e.moyenne_generale_annuelle:
            return e.moyenne_generale_annuelle
        return e.moyenne_generale if e.moyenne_generale is not None else 0

    evals_s2.sort(key=get_s2_general_sort_key, reverse=True)

    # Statistiques pour le RH
    total_evaluations = evaluations.count()
    evaluations_s1 = evaluations.filter(semestre=1).count()
    evaluations_s2 = evaluations.filter(semestre=2).count()

    # Évaluations en attente de signature directeur (pour information)
    evaluations_en_attente = Evaluation.objects.filter(
        est_signe_directeur=False,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).count()

    return render(request, "fiches/dashboard_rh.html", {
        "directions": directions,
        "evaluations": evaluations_list,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": evals_s1,
        "classement_general_s2": evals_s2,
        # Statistiques
        "total_evaluations": total_evaluations,
        "evaluations_s1": evaluations_s1,
        "evaluations_s2": evaluations_s2,
        "evaluations_en_attente": evaluations_en_attente,
    })

from django.shortcuts      import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models               import Evaluation

@login_required
def details_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # Liste des critères de rendement
    crit_re = [
        ('connaissances', evaluation.connaissances),
        ('initiative',    evaluation.initiative),
        ('rendement',     evaluation.rendement),
        ('respect_objectifs', evaluation.respect_objectifs),
    ]
    # Liste des critères de comportement
    crit_com = [
        ('civisme',          evaluation.civisme),
        ('service_public',   evaluation.service_public),
        ('relations_humaines', evaluation.relations_humaines),
        ('discipline',       evaluation.discipline),
        ('Ponctualite',      evaluation.ponctualite),
        ('assiduite',        evaluation.assiduite),
        ('tenue',            evaluation.tenue),
    ]
    # Dictionnaire d’étiquettes lisibles
    crit_labels = {
        'connaissances': 'Connaissances et aptitudes professionnelles',
        'initiative':    'Esprit d’initiative',
        'rendement':     'Puissance du travail et rendement',
        'respect_objectifs': 'Respect des Objectifs',
        'civisme':       'Civisme',
        'service_public':'Service public',
        'relations_humaines': 'Relations humaines',
        'discipline':    'Discipline',
        'Ponctualite':   'Ponctualité',
        'assiduite':     'Assiduité',
        'tenue':         'Tenue',
    }

    return render(request, "fiches/details_evaluation.html", {
        'evaluation':   evaluation,
        'crit_re':      crit_re,
        'crit_com':     crit_com,
        'crit_labels':  crit_labels,
    })

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def modifier_mot_de_passe(request):
    user        = request.user
    default_pwd = settings.DEFAULT_PASSWORD
    # indique si c'est la première connexion
    first_change = user.check_password(default_pwd)

    if request.method == 'POST':
        ancien       = request.POST.get('ancien_mdp', '').strip()
        nouveau      = request.POST.get('nouveau_mdp', '').strip()
        confirmation = request.POST.get('confirmation_mdp', '').strip()

        # 1) champs remplis ?
        if not ancien or not nouveau or not confirmation:
            messages.error(request, "Merci de remplir tous les champs.")

        # 2) nouveau ≠ confirmation ?
        elif nouveau != confirmation:
            messages.error(request, "Les mots de passe ne correspondent pas.")

        # 3) nouveau ≠ mot par défaut
        elif nouveau == default_pwd:
            messages.error(request, "Le nouveau mot de passe ne peut pas être le mot par défaut.")

        else:
            # 4) valider l'ancien mot de passe
            if first_change:
                check_ok = (ancien == default_pwd)
            else:
                check_ok = user.check_password(ancien)

            if not check_ok:
                messages.error(request, "L'ancien mot de passe est incorrect.")
            else:
                # 5) tout est OK → on met à jour
                user.set_password(nouveau)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "✅ Votre mot de passe a bien été mis à jour.")

                # 6) redirection finale selon rôle
                role = getattr(user, 'role', None)
                if role == 'agent':
                    return redirect('dashboard_agent')
                if role == 'directeur':
                    return redirect('dashboard_directeur')
                if role == 'rh':
                    return redirect('dashboard_rh')
                if role == 'dg':
                    return redirect('dashboard_dg')

                # fallback
                return redirect('login')

    # GET ou erreur de POST → affichage du formulaire
    return render(request, 'fiches/modifier_mdp1.html', {
        'first_change': first_change,
    })


from django.shortcuts import redirect

def redirection_apres_login(request):
    """Redirige l'utilisateur vers son dashboard en fonction de son rôle."""
    if request.user.is_authenticated:
        if request.user.is_directeur_general():
            return redirect('dashboard_dg')
        elif request.user.is_directeur():
            return redirect('dashboard_directeur')
        elif request.user.is_sous_directeur():
            return redirect('dashboard_sous_directeur')
        elif request.user.is_chef_service():
            return redirect('dashboard_chef_service')
        elif request.user.is_rh():
            return redirect('dashboard_rh')
        elif request.user.is_agent():
            return redirect('dashboard_agent')
    return redirect('login')

from django.contrib.auth.decorators import login_required
from fiches.models import Agent, Utilisateur, Direction
from .forms import AgentForm

@login_required
def ajouter_agent(request):
    """ Permet au RH d'ajouter un agent et de créer automatiquement un compte utilisateur """
    if not request.user.is_rh():
        return redirect('dashboard_rh')  # Seul le RH peut ajouter un agent

    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)  # ✅ On ne sauvegarde pas encore l'agent
            type_personnel = form.cleaned_data["type_personnel"]

            # ✅ Vérifier si un utilisateur existe déjà avec ce matricule
            utilisateur_existant = Utilisateur.objects.filter(username=agent.matricule).first()

            if utilisateur_existant:
                messages.error(request, "❌ Un utilisateur avec ce matricule existe déjà.")
                return redirect('ajouter_agent')

            # ✅ Création de l'utilisateur et forçage du mot de passe
            utilisateur = Utilisateur.objects.create_user(
                username=agent.matricule,  # Matricule comme identifiant
                password="0000",  # Mot de passe par défaut
                role="agent"
            )
            utilisateur.save()  # ✅ Sauvegarde explicite

            # ✅ Associer l'agent à cet utilisateur
            agent.utilisateur = utilisateur
            agent.type_personnel = type_personnel
            agent.save()  # ✅ Sauvegarde définitive

            messages.success(request, f"✅ Agent {agent.nom} ajouté avec succès ! Identifiant : {agent.matricule}, Mot de passe : ANStat@123")
            return redirect('dashboard_rh')

        else:
            messages.error(request, "❌ Erreur lors de l'ajout de l'agent.")
    else:
        form = AgentForm()

    return render(request, 'fiches/ajouter_agent.html', {'form': form})

'''
from django.contrib.auth.decorators import login_required
from .models import Agent, Evaluation, UserProfile

@login_required
def dashboard_directeur(request):
    directeur = request.user
    if not directeur.is_directeur():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas Directeur."})

    # Récupérer les agents et responsables sous la direction
    agents = Agent.objects.filter(direction=directeur.direction, type_personnel="agent").exclude(utilisateur=directeur)
    responsables = Agent.objects.filter(direction=directeur.direction, type_personnel="responsable").exclude(utilisateur=directeur)

    # Récupérer toutes les évaluations de la direction
    evaluations = Evaluation.objects.filter(agent__direction=directeur.direction)

    # Organiser les données des évaluations par agent et par semestre
    evaluations_data = {}
    # Pour les agents
    for agent in agents:
        agent_evals = evaluations.filter(agent=agent)
        evaluations_data[agent.id] = {
            's1': None,
            's2': None,
        }
        for eval in agent_evals:
            if eval.semestre == 1:
                evaluations_data[agent.id]['s1'] = {
                    'moyenne_rendement': eval.moyenne_rendement,
                    'moyenne_comportement': eval.moyenne_comportement,
                    'evaluation_id': eval.id,
                }
            elif eval.semestre == 2:
                evaluations_data[agent.id]['s2'] = {
                    'moyenne_rendement': eval.moyenne_rendement,
                    'moyenne_comportement': eval.moyenne_comportement,
                    'evaluation_id': eval.id,
                }


    # Organiser les données des évaluations par responsable et par semestre
    evaluations_data_responsables = {}
    for responsable in responsables:
        responsable_evals = evaluations.filter(agent=responsable)
        evaluations_data_responsables[responsable.id] = {
            's1': None,
            's2': None,
        }
        for eval in responsable_evals:
            if eval.semestre == 1:
                evaluations_data_responsables[responsable.id]['s1'] = {
                    'moyenne_rendement': eval.moyenne_rendement,
                    'moyenne_comportement': eval.moyenne_comportement,
                    'moyenne_management': eval.moyenne_management,
                    'evaluation_id': eval.id,
                }
            elif eval.semestre == 2:
                evaluations_data_responsables[responsable.id]['s2'] = {
                    'moyenne_rendement': eval.moyenne_rendement,
                    'moyenne_comportement': eval.moyenne_comportement,
                    'moyenne_management': eval.moyenne_management,
                    'evaluation_id': eval.id,
                }

    # Récupérer toutes les évaluations de la direction pour voir les avis des agents
    evaluations_avec_avis = Evaluation.objects.filter(
        agent__direction=directeur.direction
    ).select_related('agent').order_by('-annee', '-semestre')

    # Évaluations à signer (avis_agent rempli, pas encore signé)
    evaluations_a_signer = evaluations.filter(
        est_signe_agent=True,
        est_signe_directeur=False,
    ).exclude(avis_agent__isnull=True)

    # Filtrage dynamique par sous-direction
    sous_direction_id = request.GET.get('sous_direction')
    agents = Agent.objects.filter(direction=directeur.direction, type_personnel="agent").exclude(utilisateur=directeur)
    responsables = Agent.objects.filter(direction=directeur.direction, type_personnel="responsable").exclude(utilisateur=directeur)

    if sous_direction_id:
        agents = agents.filter(sous_direction_id=sous_direction_id)
        responsables = responsables.filter(sous_direction_id=sous_direction_id)

    # Toutes les sous-directions disponibles dans sa direction
    sous_directions = SousDirection.objects.filter(direction=directeur.direction)

    # Reste du traitement inchangé...
    evaluations = Evaluation.objects.filter(agent__in=list(agents) + list(responsables))

    # Base QS avec exclusion du directeur
    agents_qs = Agent.objects.filter(
        direction=directeur.direction, type_personnel="agent"
    ).exclude(utilisateur=directeur)

    responsables_qs = Agent.objects.filter(
        direction=directeur.direction, type_personnel="responsable"
    ).exclude(utilisateur=directeur)

    # Filtre dynamique par sous-direction (on filtre les QS existants)
    sous_direction_id = request.GET.get('sous_direction')
    if sous_direction_id:
        agents_qs = agents_qs.filter(sous_direction_id=sous_direction_id)
        responsables_qs = responsables_qs.filter(sous_direction_id=sous_direction_id)

    # Valeurs finales passées au template
    agents = agents_qs
    responsables = responsables_qs

    # Toutes les sous-directions dispo
    sous_directions = SousDirection.objects.filter(direction=directeur.direction)

    # Réutiliser ces listes pour les évaluations, avis et "à signer"
    evaluations = Evaluation.objects.filter(agent__in=list(agents) + list(responsables)).select_related('agent')

    #evaluations_avec_avis = evaluations.order_by('-annee', '-semestre')
    evaluations_avec_avis = Evaluation.objects.filter(
        agent__direction=directeur.direction,
        avis_agent__isnull=False
    ).exclude(
        avis_agent__exact=''
    ).select_related('agent').order_by('-annee', '-semestre')

    # Compter le nombre d'avis
    nombre_avis = evaluations_avec_avis.count()

    evaluations_a_signer = evaluations.filter(
        est_signe_agent=True, est_signe_directeur=False
    ).exclude(avis_agent__isnull=True)

    # Compter le nombre d'évaluations à signer
    nombre_a_signer = evaluations_a_signer.count()

    # Évaluations en attente de signature agent (pour info)
    evaluations_attente_agent = Evaluation.objects.filter(
        agent__direction=directeur.direction,
        est_signe_agent=False,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).select_related('agent').order_by('-annee', '-semestre')

    nombre_attente_agent = evaluations_attente_agent.count()

    # Profil du directeur pour la signature
    profile, created = UserProfile.objects.get_or_create(user=directeur)

    return render(request, "fiches/dashboard_directeur.html", {
        "agents": agents,
        "responsables": responsables,
        'sous_directions': sous_directions,
        'selected_sous_direction': int(sous_direction_id) if sous_direction_id else None,
        "evaluations_data": evaluations_data,
        "evaluations_data_responsables": evaluations_data_responsables,  # Ajout pour les responsables
        "evaluations_a_signer": evaluations_a_signer,
        'nombre_a_signer': nombre_a_signer,
        'evaluations_avec_avis': evaluations_avec_avis,
        'nombre_avis': nombre_avis,
        'evaluations_attente_agent': evaluations_attente_agent,
        'nombre_attente_agent': nombre_attente_agent,
        "profile": profile,

    })
'''
from django.contrib.auth.decorators import login_required
from .models import Agent, Evaluation, UserProfile


@login_required
def dashboard_directeur(request):
    directeur = request.user
    if not directeur.is_directeur():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas Directeur."})

    # Base QS avec exclusion du directeur
    agents_qs = Agent.objects.filter(
        direction=directeur.direction, type_personnel="agent"
    ).exclude(utilisateur=directeur)

    responsables_qs = Agent.objects.filter(
        direction=directeur.direction, type_personnel="responsable"
    ).exclude(utilisateur=directeur)

    # Filtre dynamique par sous-direction
    sous_direction_id = request.GET.get('sous_direction')
    if sous_direction_id:
        agents_qs = agents_qs.filter(sous_direction_id=sous_direction_id)
        responsables_qs = responsables_qs.filter(sous_direction_id=sous_direction_id)

    # Valeurs finales
    agents = agents_qs
    responsables = responsables_qs

    # Toutes les sous-directions dispo
    sous_directions = SousDirection.objects.filter(direction=directeur.direction)

    # Récupérer toutes les évaluations de la direction
    evaluations = Evaluation.objects.filter(
        agent__in=list(agents) + list(responsables)
    ).select_related('agent')

    # ====== CORRECTION ICI ======
    # Organiser les données des évaluations par agent et par semestre
    # IMPORTANT : Stocker l'objet évaluation complet, pas juste les moyennes
    evaluations_data = {}

    for agent in agents:
        agent_evals = evaluations.filter(agent=agent)
        evaluations_data[agent.id] = {
            's1': None,
            's2': None,
        }
        for eval in agent_evals:
            if eval.semestre == 1:
                evaluations_data[agent.id]['s1'] = eval  # Stocker l'objet complet
            elif eval.semestre == 2:
                evaluations_data[agent.id]['s2'] = eval  # Stocker l'objet complet

    # Organiser les données des évaluations par responsable et par semestre
    evaluations_data_responsables = {}

    for responsable in responsables:
        responsable_evals = evaluations.filter(agent=responsable)
        evaluations_data_responsables[responsable.id] = {
            's1': None,
            's2': None,
        }
        for eval in responsable_evals:
            if eval.semestre == 1:
                evaluations_data_responsables[responsable.id]['s1'] = eval  # Objet complet
            elif eval.semestre == 2:
                evaluations_data_responsables[responsable.id]['s2'] = eval  # Objet complet

    # Évaluations avec avis (exclure le directeur lui-même)
    evaluations_avec_avis = Evaluation.objects.filter(
        agent__direction=directeur.direction,
        avis_agent__isnull=False
    ).exclude(
        avis_agent__exact=''
    ).exclude(
        agent__utilisateur=directeur
    ).select_related('agent').order_by('-annee', '-semestre')

    nombre_avis = evaluations_avec_avis.count()

    # Évaluations à signer (exclure le directeur lui-même)
    evaluations_a_signer = Evaluation.objects.filter(
        agent__direction=directeur.direction,
        est_signe_agent=True,
        est_signe_directeur=False,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).exclude(
        agent__utilisateur=directeur
    ).select_related('agent').order_by('-annee', '-semestre')

    nombre_a_signer = evaluations_a_signer.count()

    # Évaluations en attente de signature agent (exclure le directeur lui-même)
    evaluations_attente_agent = Evaluation.objects.filter(
        agent__direction=directeur.direction,
        est_signe_agent=False,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).exclude(
        agent__utilisateur=directeur
    ).select_related('agent').order_by('-annee', '-semestre')

    nombre_attente_agent = evaluations_attente_agent.count()

    # Profil du directeur pour la signature
    profile, created = UserProfile.objects.get_or_create(user=directeur)

    # Récupérer la période d'évaluation active
    periode_active = PeriodeEvaluation.objects.filter(active=True).first()

    return render(request, "fiches/dashboard_directeur.html", {
        "agents": agents,
        "responsables": responsables,
        'sous_directions': sous_directions,
        'selected_sous_direction': int(sous_direction_id) if sous_direction_id else None,
        "evaluations_data": evaluations_data,
        "evaluations_data_responsables": evaluations_data_responsables,
        "evaluations_a_signer": evaluations_a_signer,
        'nombre_a_signer': nombre_a_signer,
        'evaluations_avec_avis': evaluations_avec_avis,
        'nombre_avis': nombre_avis,
        'evaluations_attente_agent': evaluations_attente_agent,
        'nombre_attente_agent': nombre_attente_agent,
        "profile": profile,
        "periode_active": periode_active,
    })

from datetime import datetime
'''
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Agent, Evaluation, JustificationNote, PeriodeEvaluation
from .forms  import EvaluationForm

@login_required
def evaluer_agent(request, agent_id):
    # 0️⃣ Vérifier qu’une période d’évaluation est active et que nous sommes dedans
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode:
        messages.error(request, "⚠️ Aucune période d’évaluation active. Contactez le service RH.")
        return redirect('dashboard_directeur')
    if today < periode.date_debut or today > periode.date_fin:
        messages.warning(
            request,
            f"🔒 La période d’évaluation va du "
            f"{periode.date_debut.strftime('%d/%m/%Y')} au {periode.date_fin.strftime('%d/%m/%Y')}. "
            "Vous ne pouvez pas évaluer en dehors de cette plage."
        )
        return redirect('dashboard_directeur')

    # 1️⃣ On est dans la période : on fixe année et semestre depuis la période RH
    annee    = periode.annee
    semestre = periode.semestre

    # 2️⃣ Charger l’agent et l’évaluation existante (le cas échéant)
    agent = get_object_or_404(Agent, id=agent_id)
    evaluation = Evaluation.objects.filter(
        agent=agent,
        annee=annee,
        semestre=semestre
    ).first()

    # 3️⃣ Préparer les justifications existantes
    justifications = {
        j.critere: j.justification
        for j in JustificationNote.objects.filter(evaluation=evaluation)
    } if evaluation else {}

    # 4️⃣ Traitement du POST
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.agent = agent
            evaluation.annee = annee
            evaluation.semestre = semestre
            evaluation.type_personnel = agent.type_personnel
            evaluation.save()
            evaluation.calcul_moyennes()

            # ✉️ Envoi de mail à l’agent
            user_agent = agent.utilisateur
            if user_agent.email:
                subject = "Votre évaluation est disponible"
                message = (
                    f"Bonjour {agent.nom} {agent.prenoms},\n\n"
                    f"Votre évaluation du semestre {semestre} de l'année {annee} "
                    f"a été réalisée le {today.strftime('%d/%m/%Y')}.\n\n"
                    "Vous pouvez la consulter sur votre espace dédié.\n\n"
                    "Cordialement,\nLe service RH"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_agent.email],
                        fail_silently=False,
                    )
                    messages.info(request, "✉️ Notification envoyée à l'agent.")
                except Exception as e:
                    messages.warning(request, f"⚠️ Erreur d’envoi du mail : {e}")

            # 📝 Enregistrement des justifications
            JustificationNote.objects.filter(evaluation=evaluation).delete()
            criteres = [
                {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
                {'nom': 'initiative', 'label': 'Esprit d\'initiative'},
                {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
                {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
                {'nom': 'civisme', 'label': 'Civisme'},
                {'nom': 'service_public', 'label': 'Sens du service public'},
                {'nom': 'relations_humaines', 'label': 'Relations humaines'},
                {'nom': 'discipline', 'label': 'Esprit de discipline'},
                {'nom': 'ponctualite', 'label': 'Ponctualité'},
                {'nom': 'assiduite', 'label': 'Assiduité'},
                {'nom': 'tenue', 'label': 'Tenue'},
            ]
            if agent.type_personnel == 'responsable':
                criteres += [
                    {'nom': 'leadership', 'label': 'Leadership'},
                    {'nom': 'planification', 'label': 'Planification'},
                    {'nom': 'travail_equipe', 'label': 'Travail d\'équipe'},
                    {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
                    {'nom': 'prise_decision', 'label': 'Prise de décision'},
                ]

            for critere in criteres:
                note = request.POST.get(critere['nom'])
                justific = request.POST.get(f"{critere['nom']}_justif", "").strip()
                if note in ['1', '5'] and justific:
                    JustificationNote.objects.create(
                        evaluation=evaluation,
                        critere=critere['nom'],
                        note=int(note),
                        justification=justific
                    )

            messages.success(request, f"✅ Évaluation du semestre {semestre}/{annee} enregistrée.")
            return redirect('dashboard_directeur')

        else:
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs et justifications.")

    # 5️⃣ GET : afficher le formulaire
    form = EvaluationForm(
        instance=evaluation
    ) if evaluation else EvaluationForm(initial={
        'annee': annee,
        'semestre': semestre,
        'type_personnel': agent.type_personnel
    })

    return render(request, 'fiches/evaluer_agent.html', {
        'form': form,
        'agent': agent,
        'semestre': semestre,
        'justifications': justifications,
    })

'''
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts       import get_object_or_404, redirect, render
from django.core.mail      import send_mail
from django.conf           import settings
from django.utils          import timezone
from django.db             import transaction

from .models   import Agent, Evaluation, JustificationNote, PeriodeEvaluation
from .forms    import EvaluationForm
@login_required
def evaluer_agent(request, agent_id):
    # 0️⃣ Vérifier la période
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode or not (periode.date_debut <= today <= periode.date_fin):
        msg = ("⚠️ Aucune période active."
               if not periode else
               f"🔒 Période du {periode.date_debut:%d/%m/%Y} au {periode.date_fin:%d/%m/%Y}.")
        messages.warning(request, msg)
        return redirect('dashboard_directeur')

    # 1️⃣ Charger agent + évaluation existante
    agent      = get_object_or_404(Agent, id=agent_id)
    annee      = periode.annee
    semestre   = periode.semestre
    evaluation = Evaluation.objects.filter(
        agent=agent, annee=annee, semestre=semestre
    ).first()

    # 2️⃣ Préparer les maps CS/SD + justifs
    CS_CRITS = [f"{nom}_chef_service" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]
    SD_CRITS = [f"{nom}_sous_directeur" for nom in [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue'
    ]]
    cs_vals = {nom: getattr(evaluation, nom, None) for nom in CS_CRITS} if evaluation else {}
    sd_vals = {nom: getattr(evaluation, nom, None) for nom in SD_CRITS} if evaluation else {}
    all_just = JustificationNote.objects.filter(evaluation=evaluation) if evaluation else []
    cs_just = {j.critere: j.justification for j in all_just if j.critere in CS_CRITS}
    sd_just = {j.critere: j.justification for j in all_just if j.critere in SD_CRITS}
    dir_just = {
        j.critere: j.justification
        for j in all_just
        if j.critere not in CS_CRITS + SD_CRITS
    }

    # 3️⃣ Définir les critères Directeur
    CRITS_DIR = [
        {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
        {'nom': 'initiative', 'label': "Esprit d’initiative"},
        {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
        {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
        {'nom': 'civisme', 'label': 'Civisme'},
        {'nom': 'service_public', 'label': 'Sens du service public'},
        {'nom': 'relations_humaines', 'label': 'Relations humaines'},
        {'nom': 'discipline', 'label': "Esprit de discipline"},
        {'nom': 'ponctualite', 'label': 'Ponctualité'},
        {'nom': 'assiduite', 'label': 'Assiduité'},
        {'nom': 'tenue', 'label': 'Tenue'},
    ]

    # 4️⃣ Traitement du POST ou préparation du GET
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            with transaction.atomic():
                ev = form.save(commit=False)
                ev.agent = agent
                ev.annee = annee
                ev.semestre = semestre
                ev.type_personnel = agent.type_personnel
                ev.save()
                ev.calcul_moyennes()
                # … gestion des mails, justifs, etc. …
            messages.success(request, "✅ Évaluation enregistrée.")
            return redirect('dashboard_directeur')
        else:
            messages.error(request, "⚠️ Formulaire invalide.")
    else:
        # Préremplir annee, semestre, type_personnel + notes existantes
        initial = {
            'annee': annee,
            'semestre': semestre,
            'type_personnel': agent.type_personnel,
        }
        if evaluation:
            for crit in CRITS_DIR:
                nom = crit['nom']
                initial[nom] = getattr(evaluation, nom, '')
        form = EvaluationForm(instance=evaluation, initial=initial)

    # 5️⃣ Construire la liste des critères à passer au template
    champs = []
    for crit in CRITS_DIR:
        nom = crit['nom']
        champs.append({
            'field':   form[nom],
            'label':   crit['label'],
            'cs_note': cs_vals.get(f"{nom}_chef_service"),
            'cs_just': cs_just.get(f"{nom}_chef_service", ""),
            'sd_note': sd_vals.get(f"{nom}_sous_directeur"),
            'sd_just': sd_just.get(f"{nom}_sous_directeur", ""),
            'dir_just':dir_just.get(nom, ""),
        })

    return render(request, 'fiches/evaluer_agent.html', {
        'agent':    agent,
        'semestre': semestre,
        'form':     form,
        'champs':   champs,
    })

'''
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Agent, Evaluation
from .forms import EvaluationForm
from datetime import datetime

@login_required
def evaluer_responsable(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id).exclude(utilisateur=request.user)

    if agent.type_personnel != 'responsable':
        messages.error(request, "Cet utilisateur n'est pas un responsable.")
        return redirect('dashboard_directeur')

    if request.user.is_directeur() and agent.direction.directeur != request.user:
        messages.error(request, "Vous ne pouvez pas évaluer ce responsable car il n'est pas dans votre direction.")
        return redirect('dashboard_directeur')

    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ La période d'évaluation n'est plus ou pas encore active. Contactez le service RH.")
        return redirect('dashboard_directeur')

    semestre = int(request.GET.get('semestre', 1))
    if semestre not in [1, 2]:
        semestre = 1

    try:
        evaluation = Evaluation.objects.get(
            agent=agent,
            annee=datetime.now().year,
            semestre=semestre
        )
    except Evaluation.DoesNotExist:
        evaluation = None

    initial_data = {
        'annee': datetime.now().year,
        'semestre': semestre,
        'type_personnel': 'responsable'
    }

    justifications = {}
    if evaluation:
        for justif in JustificationNote.objects.filter(evaluation=evaluation):
            justifications[justif.critere] = justif.justification

    if request.method == "POST":
        print("Données POST :", request.POST)
        form = EvaluationForm(request.POST, instance=evaluation) if evaluation else EvaluationForm(request.POST, initial=initial_data)

        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.agent = agent
            evaluation.semestre = semestre
            evaluation.type_personnel = 'responsable'
            evaluation.save()
            evaluation.calcul_moyennes()

            user_agent = agent.utilisateur  # ou evaluation.agent.utilisateur
            if user_agent.email:
                subject = "Votre évaluation est disponible"
                message = (
                    f"Bonjour {agent.nom} {agent.prenoms},\n\n"
                    f"Votre évaluation du semestre {semestre} de l'année {evaluation.annee} "
                    f"a été réalisée par votre directeur le {timezone.now().strftime('%d/%m/%Y')}.\n\n"
                    "Vous pouvez la consulter depuis votre espace dédié sur le site (evaluation.stats.ci).\n\n"
                    "Cordialement,\n"
                    "Le service RH"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_agent.email],
                        fail_silently=False,
                    )
                    messages.info(request, "✉️ Un email de notification a été envoyé à l'agent.")
                except Exception as e:
                    messages.warning(request, f"⚠️ Impossible d'envoyer l'email : {e}")
            JustificationNote.objects.filter(evaluation=evaluation).delete()

            criteres = [
                {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
                {'nom': 'initiative', 'label': 'Esprit d\'initiative'},
                {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
                {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
                {'nom': 'civisme', 'label': 'Civisme'},
                {'nom': 'service_public', 'label': 'Sens du service public'},
                {'nom': 'relations_humaines', 'label': 'Relations humaines'},
                {'nom': 'discipline', 'label': 'Esprit de discipline'},
                {'nom': 'ponctualité', 'label': 'Ponctualité'},
                {'nom': 'assiduite', 'label': 'Assiduité'},
                {'nom': 'tenue', 'label': 'Tenue'},
                {'nom': 'leadership', 'label': 'Leadership'},
                {'nom': 'planification', 'label': 'Planification'},
                {'nom': 'travail_equipe', 'label': 'Travail d\'équipe'},
                {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
                {'nom': 'prise_decision', 'label': 'Prise de décision'},
            ]

            for critere in criteres:
                note = request.POST.get(critere['nom'])
                justification = request.POST.get(f"{critere['nom']}_justif", "").strip()
                if note in ['1', '5'] and justification:
                    JustificationNote.objects.create(
                        evaluation=evaluation,
                        critere=critere['nom'],
                        note=int(note),
                        justification=justification
                    )
                    print(f"✅ Justification enregistrée pour {critere['nom']}: {justification}")

            messages.success(request, f"✅ Évaluation du semestre {semestre} enregistrée avec succès.")
            return redirect('dashboard_directeur')
        else:
            print("❌ Erreurs du formulaire :", form.errors)
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs et justifications.")

    else:
        form = EvaluationForm(instance=evaluation) if evaluation else EvaluationForm(initial=initial_data)

    # Définir les listes de critères pour le template
    criteres_rendement = ['connaissances', 'initiative', 'rendement', 'respect_objectifs']
    criteres_comportement = ['civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualité', 'assiduite', 'tenue']
    criteres_management = ['leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision']

    return render(request, 'fiches/evaluer_responsable.html', {
        'form': form,
        'agent': agent,
        'poste': getattr(agent, 'poste', 'Non défini'),
        'tenu_depuis': getattr(agent, 'tenu_depuis', 'Non défini'),
        'semestre': semestre,
        'justifications': justifications,
        'criteres_rendement': criteres_rendement,
        'criteres_comportement': criteres_comportement,
        'criteres_management': criteres_management,
    })
'''

# vues.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import Agent, Evaluation, PeriodeEvaluation, JustificationNote
from .forms import EvaluationForm

@login_required
def evaluer_responsable(request, agent_id):
    # 0) Période d’évaluation
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode or not (periode.date_debut <= today <= periode.date_fin):
        msg = ("⚠️ Aucune période active."
               if not periode else
               f"🔒 Période du {periode.date_debut:%d/%m/%Y} au {periode.date_fin:%d/%m/%Y}.")
        messages.warning(request, msg)
        return redirect('dashboard_directeur')

    # 1) Agent + garde-fous
    agent = get_object_or_404(Agent, id=agent_id)
    if agent.type_personnel != 'responsable':
        messages.error(request, "Cet agent n'est pas un responsable.")
        return redirect('dashboard_directeur')

    # (Optionnel) restriction: seul le directeur de la direction de l’agent peut l’évaluer
    if hasattr(agent, "direction") and hasattr(agent.direction, "directeur"):
        if request.user.is_authenticated and hasattr(request.user, "is_directeur") and callable(request.user.is_directeur):
            if request.user.is_directeur() and agent.direction.directeur != request.user:
                messages.error(request, "Vous ne pouvez pas évaluer ce responsable (hors de votre direction).")
                return redirect('dashboard_directeur')

    annee = periode.annee
    semestre = periode.semestre

    # 2) Évaluation existante
    evaluation = Evaluation.objects.filter(
        agent=agent, annee=annee, semestre=semestre
    ).first()

    # 3) Colonnes CS/SD + justifs existantes
    base_crit_names = [
        'connaissances','initiative','rendement','respect_objectifs',
        'civisme','service_public','relations_humaines','discipline',
        'ponctualite','assiduite','tenue',
        # Critères de management
        'leadership','planification','travail_equipe','resolution_problemes','prise_decision'
    ]
    SD_CRITS = [f"{nom}_sous_directeur" for nom in base_crit_names]

    if evaluation:
        sd_vals = {nom: getattr(evaluation, nom, None) for nom in SD_CRITS}
        all_just = JustificationNote.objects.filter(evaluation=evaluation)
    else:
        sd_vals = {}
        all_just = []

    sd_just = {j.critere: j.justification for j in all_just if j.critere in SD_CRITS}
    dir_just = {j.critere: j.justification for j in all_just
                if j.critere not in SD_CRITS}

    # 4) Liste des critères à afficher pour le Directeur (11 communs + 5 management)
    CRITS_DIR = [
        {'nom': 'connaissances',      'label': 'Connaissances et aptitudes professionnelles'},
        {'nom': 'initiative',         'label': "Esprit d’initiative"},
        {'nom': 'rendement',          'label': 'Puissance du travail et rendement'},
        {'nom': 'respect_objectifs',  'label': 'Respect des objectifs'},

        {'nom': 'civisme',            'label': 'Civisme'},
        {'nom': 'service_public',     'label': 'Sens du service public'},
        {'nom': 'relations_humaines', 'label': 'Relations humaines'},
        {'nom': 'discipline',         'label': "Esprit de discipline"},
        {'nom': 'ponctualite',        'label': 'Ponctualité'},
        {'nom': 'assiduite',          'label': 'Assiduité'},
        {'nom': 'tenue',              'label': 'Tenue'},
    ]
    # Ajout des critères Management pour les responsables
    CRITS_DIR += [
        {'nom': 'leadership',           'label': 'Leadership'},
        {'nom': 'planification',        'label': 'Planification'},
        {'nom': 'travail_equipe',       'label': "Travail d’équipe"},
        {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
        {'nom': 'prise_decision',       'label': 'Prise de décision'},
    ]

    # 5) POST / GET
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            with transaction.atomic():
                ev = form.save(commit=False)
                ev.agent = agent
                ev.annee = annee
                ev.semestre = semestre
                ev.type_personnel = 'responsable'
                ev.save()

                # (ré)calcule les moyennes si ton modèle le prévoit
                if hasattr(ev, "calcul_moyennes"):
                    ev.calcul_moyennes()

                # Justifications du Directeur (notes 1 ou 5)
                JustificationNote.objects.filter(evaluation=ev).exclude(
                    critere__in= SD_CRITS
                ).delete()

                for crit in CRITS_DIR:
                    nom = crit['nom']
                    note = request.POST.get(nom)
                    just_text = (request.POST.get(f"{nom}_justif", "") or "").strip()
                    if note in ("1", "5") and just_text:
                        JustificationNote.objects.create(
                            evaluation=ev, critere=nom, note=int(note), justification=just_text
                        )

            messages.success(request, "✅ Évaluation du responsable enregistrée.")
            return redirect('dashboard_directeur')
        else:
            messages.error(request, "⚠️ Formulaire invalide. Merci de vérifier les champs.")
    else:
        # Pré-remplir annee/semestre/type + notes existantes
        initial = {'annee': annee, 'semestre': semestre, 'type_personnel': 'responsable'}
        if evaluation:
            for crit in CRITS_DIR:
                nom = crit['nom']
                initial[nom] = getattr(evaluation, nom, '')
        form = EvaluationForm(instance=evaluation, initial=initial)

    # 6) Construire la liste "champs" pour le template (affichage tabulaire)
    champs = []
    for crit in CRITS_DIR:
        nom = crit['nom']
        champs.append({
            'label':   crit['label'],
            'field':   form[nom],  # <select> du Directeur
            'sd_note': sd_vals.get(f"{nom}_sous_directeur"),
            'sd_just': sd_just.get(f"{nom}_sous_directeur", ""),
            'dir_just': dir_just.get(nom, ""),
        })

    return render(request, 'fiches/evaluer_responsable.html', {
        'agent': agent,
        'semestre': semestre,
        'form': form,
        'champs': champs,
    })

'''
from xhtml2pdf import pisa

# fiches/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Agent, Evaluation
from .forms import AgentForm, AvisAgentForm


@login_required
def dashboard_agent(request):
    """Afficher les informations et permettre à l'agent de donner son avis sur l'évaluation."""
    # Récupérer l'agent associé à l'utilisateur connecté
    agent = get_object_or_404(Agent, utilisateur=request.user)  # Changé 'user' en 'utilisateur'

    # Récupérer toutes les évaluations de l'agent, triées par année et semestre décroissants
    evaluations = Evaluation.objects.filter(agent=agent).order_by('-annee', '-semestre')
    derniere_evaluation = evaluations.first()  # Dernière évaluation (peut être None)

    # Initialiser les formulaires
    form = AgentForm(instance=agent)
    avis_form = AvisAgentForm(instance=derniere_evaluation) if derniere_evaluation else None

    # Gérer les requêtes POST
    if request.method == "POST":
        if "update_info" in request.POST:
            form = AgentForm(request.POST, instance=agent)
            if form.is_valid():
                form.save()
                return redirect('dashboard_agent')
        elif "update_avis" in request.POST and derniere_evaluation:
            avis_form = AvisAgentForm(request.POST, instance=derniere_evaluation)
            if avis_form.is_valid():
                avis_form.save()
                return redirect('dashboard_agent')

    return render(request, 'fiches/dashboard_agent.html', {
        'agent': agent,
        'evaluations': evaluations,
        'derniere_evaluation': derniere_evaluation,
        'form': form,
        'avis_form': avis_form,
        'type_personnel': agent.type_personnel
    })'''


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from .models import Agent, Evaluation
from .forms import AgentForm, AvisAgentForm


@login_required
def dashboard_agent(request):
    """
    Dashboard de l'agent/responsable.
    Affiche les évaluations uniquement si elles ont été complétées par le directeur.
    """
    # Récupérer l'agent associé à l'utilisateur connecté
    try:
        agent = Agent.objects.get(utilisateur=request.user)
    except Agent.DoesNotExist:
        messages.error(request, "Aucun agent associé à ce compte.")
        return render(request, 'fiches/erreur.html', {
            'message': "Aucun agent associé à ce compte."
        })

    # Type de personnel (agent ou responsable)
    type_personnel = agent.type_personnel

    # Année courante
    annee_courante = datetime.now().year

    # Récupérer uniquement les évaluations COMPLÉTÉES (avec des notes)
    # On vérifie qu'au moins moyenne_generale existe et n'est pas nulle
    evaluations = Evaluation.objects.filter(
        agent=agent,
        annee=annee_courante,
        moyenne_generale__isnull=False  # Vérifier que l'évaluation est complète
    ).exclude(
        moyenne_generale=0  # Exclure les évaluations vides
    ).order_by('semestre')

    # Historique (années précédentes) - aussi filtrées
    evaluations_historique = Evaluation.objects.filter(
        agent=agent,
        annee__lt=annee_courante,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).order_by('-annee', 'semestre')

    # Liste des années disponibles pour le filtre historique
    annees_disponibles = Evaluation.objects.filter(
        agent=agent,
        annee__lt=annee_courante,
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).values_list('annee', flat=True).distinct().order_by('-annee')

    # Initialiser les formulaires
    form = AgentForm(instance=agent)

    # Formulaire d'avis pour la dernière évaluation non verrouillée
    derniere_evaluation = evaluations.filter(
        est_signe_directeur=False
    ).first()
    avis_form = AvisAgentForm(instance=derniere_evaluation) if derniere_evaluation else None

    # Gérer les requêtes POST
    if request.method == "POST":
        if "update_info" in request.POST:
            form = AgentForm(request.POST, instance=agent)
            if form.is_valid():
                form.save()
                messages.success(request, "✅ Vos informations ont été mises à jour.")
                return redirect('dashboard_agent')
            else:
                messages.error(request, "⚠️ Erreur lors de la mise à jour.")

        elif "update_avis" in request.POST and derniere_evaluation:
            avis_form = AvisAgentForm(request.POST, instance=derniere_evaluation)
            if avis_form.is_valid():
                avis_form.save()
                messages.success(request, "✅ Votre avis a été enregistré.")
                return redirect('dashboard_agent')
            else:
                messages.error(request, "⚠️ Erreur lors de l'enregistrement de l'avis.")

    context = {
        'agent': agent,
        'type_personnel': type_personnel,
        'annee_courante': annee_courante,
        'evaluations': evaluations,
        'evaluations_historique': evaluations_historique,
        'annees_disponibles': annees_disponibles,
        'derniere_evaluation': derniere_evaluation,
        'form': form,
        'avis_form': avis_form,
    }

    return render(request, 'fiches/dashboard_agent.html', context)

import os
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

import pdfkit

from fiches.models import Evaluation
# from userprofiles.models import UserProfile  # si besoin

@login_required
def generer_fiche_evaluation_pdf(request, evaluation_id):
    # petit helper pour convertir un chemin disque en URI file://
    def to_uri(path: str | os.PathLike | None) -> str | None:
        if not path:
            return None
        try:
            return Path(path).absolute().as_uri()  # -> file:///C:/...
        except Exception:
            return None

    # 1) Récupération de l’évaluation et de l’agent
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    agent = evaluation.agent

    # ✅ Autorisation RH, directeur ou agent
    if request.user.is_rh():
        pass  # Le RH peut tout voir
    elif request.user.is_directeur():
        if agent.direction.directeur != request.user:
            return HttpResponse("403 – Pas autorisé", status=403)
        if not evaluation.avis_agent:
            return HttpResponse("403 – L'agent doit d'abord donner son avis", status=403)
    elif request.user == agent.utilisateur:
        if not (evaluation.est_signe_agent and evaluation.est_signe_directeur):
            messages.error(request, "La fiche n’a pas encore été signée par toutes les parties.")
            return redirect('dashboard_agent')
    else:
        return HttpResponse("403 – Accès refusé", status=403)

    raw = evaluation.decision_finale or ""
    try:
        decs = json.loads(raw) if raw.strip().startswith('[') else raw
    except Exception:
        decs = raw
    if isinstance(decs, str):
        decs_list = [p.strip() for p in decs.split(',') if p.strip()]
    elif isinstance(decs, (list, tuple, set)):
        decs_list = list(decs)
    else:
        decs_list = []

    # 3) Construction des URI pour entête/pied
    entete_fs = finders.find('images/entete.png')
    pied_fs   = finders.find('images/pied.png')
    entete_uri = Path(entete_fs).absolute().as_uri() if entete_fs else ''
    pied_uri   = Path(pied_fs).absolute().as_uri()   if pied_fs   else ''

    # 4) Signatures (inchangé)
    signature = evaluation.get_signature_directeur()
    signature_path = Path(os.path.join(settings.MEDIA_ROOT, str(signature))).absolute().as_uri() if signature else None
    profile_agent = UserProfile.objects.filter(user=agent.utilisateur).first()
    signature_agent_path = Path(os.path.join(settings.MEDIA_ROOT, str(profile_agent.signature))).absolute().as_uri() if profile_agent and profile_agent.signature else None
    profile_dg = UserProfile.objects.filter(user=request.user).first()  # adapte si le PDF est généré par un autre user
    #signature_dg_path = to_uri(profile_dg.signature.path) if getattr(profile_dg, "signature", None) else None

    # si tu stockes la signature du DG sur Evaluation.signature_dg
    if getattr(evaluation, "signature_dg", None):
        signature_dg_path = Path(os.path.join(settings.MEDIA_ROOT, str(evaluation.signature_dg))).absolute().as_uri()
    else:
        # sinon depuis le profil de l'utilisateur qui a signé en DG
        prof_dg = UserProfile.objects.filter(
            user=evaluation.utilisateur_signature_dg).first() if evaluation.utilisateur_signature_dg else None
        signature_dg_path = Path(os.path.join(settings.MEDIA_ROOT,
                                              str(prof_dg.signature))).absolute().as_uri() if prof_dg and prof_dg.signature else None

    # 5) Contexte
    context = {
        'evaluation': evaluation,
        'agent': agent,
        'entete_path': entete_uri,
        'pied_path': pied_uri,
        'signature_path': signature_path,
        'signature_agent_path': signature_agent_path,
        "signature_dg_path": signature_dg_path,
        'request': request,
        'generation_date': timezone.now(),
        "decisions_list": decs_list,
    }

    # 6) Rendu HTML principal et footer
    html = render_to_string('fiches/fiche_evaluation_pdf.html', context)
    footer_html = render_to_string('fiches/footer_pdf.html', context)

    # 7) Écrire ces HTML dans deux fichiers temporaires
    tmp_html = tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8')
    tmp_html.write(html)
    tmp_html.flush()
    tmp_html.close()
    html_path = tmp_html.name

    tmp_footer = tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8')
    tmp_footer.write(footer_html)
    tmp_footer.flush()
    tmp_footer.close()
    footer_uri = Path(tmp_footer.name).absolute().as_uri()

    # 8) Options pdfkit avec accès local forcé
    options = {
        'enable-local-file-access': None,
        'encoding': 'UTF-8',
        'page-size': 'A4',
        'margin-bottom': '50mm',
        'footer-html': footer_uri,
        'footer-spacing': '10',
    }
    config = None
    if getattr(settings, 'WKHTMLTOPDF_CMD', None):
        config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_CMD)

    # 9) Génération du PDF depuis le fichier .html
    try:
        pdf = pdfkit.from_file(html_path, False, configuration=config, options=options)
    except Exception as e:
        return HttpResponse(f"Erreur lors de la génération du PDF : {e}", status=500)
    finally:
        # Nettoyage des fichiers temporaires
        os.remove(html_path)
        os.remove(tmp_footer.name)

    # 10) Envoi du PDF en réponse
    filename = f"fiche_evaluation_{agent.matricule}_{evaluation.annee}_{evaluation.semestre}.pdf"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# fiches/views.py
@login_required
def ajouter_avis_agent(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    if request.user != evaluation.agent.utilisateur:
        return HttpResponse("Vous n'avez pas l'autorisation de modifier cette évaluation.", status=403)

    if request.method == 'POST':
        avis = request.POST.get('avis_agent')
        if avis:
            evaluation.avis_agent = avis
            evaluation.save()
            return redirect('dashboard_agent')
        return HttpResponse("L'avis ne peut pas être vide.", status=400)

    return render(request, 'fiches/ajouter_avis_agent.html', {'evaluation': evaluation})

@login_required
def signer_evaluation(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    if not request.user.is_directeur() or evaluation.agent.direction.directeur != request.user:
        return HttpResponse("Vous n'avez pas l'autorisation de signer cette évaluation.", status=403)
    if not evaluation.avis_agent:
        return HttpResponse("L'agent doit d'abord donner son avis avant que vous puissiez signer.", status=403)
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.signature:
        return HttpResponse("Vous devez d'abord ajouter une signature à votre profil.", status=403)

    if request.method == 'POST':
        evaluation.est_signe = True
        evaluation.save()
        return redirect('dashboard_directeur')  # Redirige vers un tableau de bord directeur

    return render(request, 'fiches/signer_evaluation.html', {'evaluation': evaluation})


# Vue pour permettre au directeur d'ajouter sa signature à son profil (optionnel)
@login_required
def modifier_profil_directeur(request):
    if not request.user.is_directeur():
        return HttpResponse("Vous n'avez pas l'autorisation d'accéder à cette page.", status=403)

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        signature = request.FILES.get('signature')
        if signature:
            profile.signature = signature
            profile.save()
            return redirect('dashboard_directeur')
        return HttpResponse("Aucune signature fournie.", status=400)

    return render(request, 'fiches/modifier_profil_directeur.html', {'profile': profile})

from django.utils import timezone
@login_required
def signer_evaluation_agent(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    if request.user.is_agent() and evaluation.agent.utilisateur != request.user:
        return redirect('dashboard_agent')

    if request.method == "POST":
        evaluation.est_signe_agent = True
        evaluation.date_signature_agent = timezone.now().date()
        evaluation.save()
        messages.success(request, "✅ Vous avez signé votre évaluation.")
        return redirect('dashboard_agent')

    return render(request, 'fiches/signer_evaluation_agent.html', {'evaluation': evaluation})

@login_required
def signer_evaluation_directeur(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    if not request.user.is_directeur() or evaluation.agent.direction.directeur != request.user:
        return redirect('dashboard_directeur')

    if not evaluation.est_signe_agent:
        messages.warning(request, "⛔ L'agent n'a pas encore signé son évaluation.")
        return redirect('dashboard_directeur')

    if request.method == "POST":
        evaluation.est_signe_directeur = True
        evaluation.save()

        # 2️⃣ Envoi de l'email de notification à l'agent
        user_agent = evaluation.agent.utilisateur
        if user_agent.email:
            subject = "Votre évaluation a été validée"
            message = (
                f"Bonjour {evaluation.agent.nom} { evaluation.agent.prenoms },\n\n"
                f"Votre évaluation du semestre {evaluation.semestre} de l'année {evaluation.annee} "
                f"a été signée par votre directeur le {timezone.now().strftime('%d/%m/%Y')}.\n"
                f"Vous pouvez la télécharger dans votre espace dedié sur le site (evaluation.stats.ci).\n\n"
                "Cordialement,\n"
                "Le service RH"
            )
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_agent.email],
                    fail_silently=False,
                )
                messages.success(request, "✅ Email de notification envoyé à l'agent.")
            except Exception as e:
                messages.error(request, f"⚠️ Erreur lors de l'envoi de l'email : {e}")

        messages.success(request, "✅ Évaluation signée en tant que directeur.")
        return redirect('dashboard_directeur')

    return render(request, 'fiches/signer_evaluation_directeur.html', {'evaluation': evaluation})

'''@login_required
def gerer_signature_utilisateur(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST" and request.FILES.get("signature"):
        profile.signature = request.FILES["signature"]
        profile.save()
        messages.success(request, "✅ Signature enregistrée avec succès.")
        return redirect('dashboard_agent' if user.is_agent() else 'dashboard_directeur')

    return render(request, 'fiches/gerer_signature.html', {'profile': profile})'''


# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.images import get_image_dimensions
from django.core.exceptions import ValidationError

from .models import UserProfile

MAX_FILE_SIZE_MB = 2  # limite 2 Mo

@login_required
def gerer_signature_utilisateur(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        file = request.FILES.get("signature")
        if not file:
            messages.error(request, "Veuillez sélectionner un fichier d'image.")
            return redirect(request.path)

        # ✅ Vérif taille
        if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            messages.error(request, f"Fichier trop volumineux (>{MAX_FILE_SIZE_MB} Mo).")
            return redirect(request.path)

        # ✅ Vérif type (MIME) + lecture dimensions (déclenche une validation image si non image)
        valid_mimes = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
        if getattr(file, "content_type", "").lower() not in valid_mimes:
            messages.error(request, "Format non supporté. Utilisez PNG, JPG ou WEBP.")
            return redirect(request.path)

        try:
            # force l'ouverture pour s'assurer que c'est bien une image
            get_image_dimensions(file)
        except Exception:
            messages.error(request, "Le fichier n'est pas une image valide.")
            return redirect(request.path)

        # ✅ Enregistrement
        profile.signature = file
        profile.save()
        messages.success(request, "✅ Signature enregistrée avec succès.")

        # ✅ Redirection selon le rôle
        if hasattr(user, "is_directeur_general") and user.is_directeur_general():
            return redirect('dashboard_dg')
        elif hasattr(user, "is_directeur") and user.is_directeur():
            return redirect('dashboard_directeur')
        elif hasattr(user, "is_agent") and user.is_agent():
            return redirect('dashboard_agent')

        # fallback
        return redirect('home')

    return render(request, 'fiches/gerer_signature.html', {'profile': profile})



'''

@login_required
def dashboard_dg(request):
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # Récupérer toutes les directions (puisque le RH n'a pas de direction, mais les agents oui)
    directions = Direction.objects.all()

    # Récupérer les filtres
    direction_filter = request.GET.get('direction', 'all')
    annee_filter = request.GET.get('annee', '')
    semestre_filter = request.GET.get('semestre', '')

    # Récupérer toutes les évaluations (sans restriction de direction pour le RH)
    evaluations = Evaluation.objects.all().select_related('agent', 'agent__direction')

    # Appliquer les filtres
    if direction_filter != 'all':
        evaluations = evaluations.filter(agent__direction__id=direction_filter)
    if annee_filter:
        evaluations = evaluations.filter(annee=annee_filter)
    if semestre_filter:
        evaluations = evaluations.filter(semestre=semestre_filter)

    # Convertir en liste pour tri personnalisé
    evaluations_list = list(evaluations)

    # Séparer ceux qui n'ont pas de moyenne, pour ne pas les trier
    avec_note = [e for e in evaluations_list if e.moyenne_generale is not None]
    sans_note = [e for e in evaluations_list if e.moyenne_generale is None]

    # Trier uniquement ceux qui ont une note
    avec_note.sort(key=lambda e: e.moyenne_generale, reverse=True)

    # Reconstituer la liste finale
    evaluations_list = avec_note + sans_note

    # Trier les évaluations pour l'affichage dans "Liste des Évaluations"
    evaluations_list.sort(
        key=lambda
            eval: eval.moyenne_generale_annuelle if eval.semestre == 2 and eval.moyenne_generale_annuelle is not None else eval.moyenne_generale,
        reverse=True
    )
    evaluations_list.sort(
        key=lambda e: (
            e.moyenne_generale
            if e.moyenne_generale is not None
            else float('-inf')
        ),
        reverse=True
    )

    # Récupérer les années disponibles pour le filtre
    annees = Evaluation.objects.all().values_list('annee', flat=True).distinct().order_by('-annee')

    # Récupérer les semestres pour le filtre
    #semestres = Evaluation.SEMESTRE_CHOICES

    # Classement par direction (séparé par semestre)
    classements_par_direction = {}
    for direction in directions:
        # Filtrer les évaluations de cette direction
        evals = [e for e in evaluations_list if e.agent.direction == direction]

        # Séparer par semestre
        evals_s1 = [e for e in evals if e.semestre == 1]
        evals_s2 = [e for e in evals if e.semestre == 2]

        # Trier S1 par moyenne_generale
        evals_s1.sort(key=lambda e: e.moyenne_generale, reverse=True)
        # Trier S2 par moyenne_generale_annuelle (si disponible)
        evals_s2.sort(
            key=lambda
                e: e.moyenne_generale_annuelle if e.moyenne_generale_annuelle is not None else e.moyenne_generale,
            reverse=True
        )

        # Stocker les classements par semestre
        classements_par_direction[direction] = {
            's1': evals_s1,
            's2': evals_s2
        }

    # Classement général (séparé par semestre)
    evals_s1 = [e for e in evaluations_list if e.semestre == 1]
    evals_s2 = [e for e in evaluations_list if e.semestre == 2]

    # Trier S1 par moyenne_generale
    evals_s1.sort(key=lambda e: e.moyenne_generale, reverse=True)
    # Trier S2 par moyenne_generale_annuelle (si disponible)
    evals_s2.sort(
        key=lambda e: e.moyenne_generale_annuelle if e.moyenne_generale_annuelle is not None else e.moyenne_generale,
        reverse=True
    )
    directeurs = Utilisateur.objects.filter(role='directeur')
    eval_form = EvaluationForm()
    return render(request, "fiches/dashboard_dg.html", {
        "directions": directions,  # Toutes les directions
        "evaluations": evaluations_list,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,
        #"semestres": semestres,
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": evals_s1,
        "classement_general_s2": evals_s2,
        'directeurs': directeurs,
        'eval_form': eval_form,
    })
'''
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.db import models

from .models import Utilisateur, Evaluation, Direction
from .forms import EvaluationForm
from .models import Utilisateur, Evaluation, Agent
# vues.py
from .models import Utilisateur, Evaluation, Agent  # ← importe Agent si séparé

@login_required
def dashboard_dg(request):
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    def _key_moy(e):
        # clé de tri pour S1 (moyenne_generale), None => -inf pour passer en fin
        return e.moyenne_generale if e.moyenne_generale is not None else float('-inf')

    def _key_annuelle(e):
        # clé de tri pour S2 : annuelle si dispo, sinon moyenne_generale, sinon -inf
        mg = e.moyenne_generale if e.moyenne_generale is not None else float('-inf')
        mga = getattr(e, 'moyenne_generale_annuelle', None)
        return mga if mga is not None else mg

    directions = Direction.objects.all()
    direction_filter = request.GET.get('direction', 'all')
    annee_filter     = request.GET.get('annee', '')
    semestre_filter  = request.GET.get('semestre', '')

    evaluations = Evaluation.objects.all().select_related('agent', 'agent__direction')
    if direction_filter != 'all':
        evaluations = evaluations.filter(agent__direction__id=direction_filter)
    if annee_filter:
        evaluations = evaluations.filter(annee=annee_filter)
    if semestre_filter:
        evaluations = evaluations.filter(semestre=semestre_filter)

    evaluations_list = list(evaluations)
    avec_note  = [e for e in evaluations_list if e.moyenne_generale is not None]
    sans_note  = [e for e in evaluations_list if e.moyenne_generale is None]
    avec_note.sort(key=lambda e: e.moyenne_generale, reverse=True)
    evaluations_list = avec_note + sans_note

    annees = (Evaluation.objects
              .values_list('annee', flat=True)
              .distinct()
              .order_by('-annee'))

    # Classements
    classements_par_direction = {}
    for direction in directions:
        ev_dir = [e for e in evaluations_list if e.agent.direction == direction]
        s1 = [e for e in ev_dir if e.semestre == 1]
        s2 = [e for e in ev_dir if e.semestre == 2]
        s1.sort(key=lambda e: e.moyenne_generale if e.moyenne_generale is not None else float('-inf'), reverse=True)
        s2.sort(
            key=lambda e: (
                e.moyenne_generale_annuelle
                if getattr(e, 'moyenne_generale_annuelle', None) is not None
                else (e.moyenne_generale if e.moyenne_generale is not None else float('-inf'))
            ),
            reverse=True
        )
        classements_par_direction[direction] = {'s1': s1, 's2': s2}

    classement_general_s1 = sorted(
        (e for e in evaluations_list if e.semestre == 1),
        key=_key_moy,
        reverse=True
    )
    classement_general_s2 = sorted(
        (e for e in evaluations_list if e.semestre == 2),
        key=_key_annuelle,
        reverse=True
    )

    # === Section "Évaluer Directeur" ===
    directeurs = Utilisateur.objects.filter(role='directeur')

    # Récupère les Agents liés à ces Utilisateur d’un coup (ADAPTE le champ selon ton modèle)
    # Si le champ s’appelle Agent.utilisateur :
    agents = Agent.objects.filter(utilisateur__in=directeurs).select_related('direction')
    # Si chez toi c’est Agent.user, remplace la ligne ci-dessus par :
    # agents = Agent.objects.filter(user__in=directeurs).select_related('direction')

    # Map rapide user_id -> Agent
    # (utilise .utilisateur_id ou .user_id selon ton modèle)
    user_to_agent = {a.utilisateur_id: a for a in agents}
    # Si c’est .user_id :
    # user_to_agent = {a.user_id: a for a in agents}

    # Map user_id -> Agent
    user_to_agent = {a.utilisateur_id: a for a in agents}

    # Map directeur(user) -> agent.id (ou None si pas d'agent lié)
    directeur_to_agent = {
        d.id: (user_to_agent[d.id].id if d.id in user_to_agent else None)
        for d in directeurs
    }

    evaluations_data_responsables = {}
    for d in directeurs:
        agent = user_to_agent.get(d.id)
        if agent is not None:
            s1 = Evaluation.objects.filter(agent=agent, semestre=1).order_by('-annee').first()
            s2 = Evaluation.objects.filter(agent=agent, semestre=2).order_by('-annee').first()
        else:
            s1 = None
            s2 = None
        evaluations_data_responsables[d.id] = {'s1': s1, 's2': s2}

    eval_form = EvaluationForm()

    # Map rapide: id du directeur (Utilisateur) -> id de l'Agent (ou None)
    directeurs_agents_ids = {
        d.id: (user_to_agent[d.id].id if d.id in user_to_agent else None)
        for d in directeurs
    }

    return render(request, "fiches/dashboard_dg.html", {
        "directions": directions,
        "evaluations": evaluations_list,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": classement_general_s1,
        "classement_general_s2": classement_general_s2,
        "directeurs": directeurs,
        "evaluations_data_responsables": evaluations_data_responsables,  # ← passe au template
        "eval_form": eval_form,
        "directeur_to_agent": directeur_to_agent,
        "directeurs_agents_ids": directeurs_agents_ids,
    })
"""
'''
# fiches/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages
from django.db.models import Q

from .models import Utilisateur, Evaluation, Direction, Agent
from .forms import EvaluationForm


@login_required
def dashboard_dg(request):
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # -------- Filtres formulaire --------
    directions       = Direction.objects.all()
    direction_filter = request.GET.get('direction', 'all')
    annee_filter     = request.GET.get('annee') or None
    semestre_filter  = request.GET.get('semestre') or None

    signed_by_evaluator_q = (
            Q(agent__utilisateur__role='directeur', est_signe_agent=True) |
            Q(~Q(agent__utilisateur__role='directeur'), est_signe_directeur=True)
    )

    # -------- Base queryset : uniquement signé par le Directeur (de direction) --------
    base_qs = (
        Evaluation.objects
        .filter(signed_by_evaluator_q)  # 🔴 clé : rien ne remonte au DG avant la signature du Directeur
        .select_related('agent', 'agent__direction', 'agent__utilisateur')
    )

    # Appliquer les filtres (si présents)
    if direction_filter and direction_filter != 'all':
        base_qs = base_qs.filter(agent__direction_id=direction_filter)
    if annee_filter:
        base_qs = base_qs.filter(annee=annee_filter)
    if semestre_filter:
        base_qs = base_qs.filter(semestre=semestre_filter)

    # -------- Onglet "Liste des évaluations" (le DG pose la décision) --------
    evaluations = base_qs.order_by('-annee', '-semestre', 'agent__nom', 'agent__prenoms')

    # -------- Onglet "Évaluations à signer" (décision posée, pas encore signée par le DG) --------
    evaluations_a_signer = (
        base_qs
        .filter(est_signe_dg=False)             # pas signé par le DG
        .exclude(Q(decision_finale__isnull=True) | Q(decision_finale=""))  # décision présente
        .order_by('-annee', '-semestre')
    )

    def _mark_signed_by_evaluator(qs):
        for e in qs:
            # si l’agent évalué est un directeur → on attend la signature agent
            is_dir = getattr(getattr(e.agent, 'utilisateur', None), 'role', None) == 'directeur'
            e.signed_by_evaluator = e.est_signe_agent if is_dir else e.est_signe_directeur
        return qs

    evaluations = _mark_signed_by_evaluator(list(evaluations))
    evaluations_a_signer = _mark_signed_by_evaluator(list(evaluations_a_signer))

    # -------- Données pour Classements (facultatif, inchangé sauf qu’on part de base_qs) --------
    def _key_moy(e):
        return e.moyenne_generale if e.moyenne_generale is not None else float('-inf')

    def _key_annuelle(e):
        mg = e.moyenne_generale if e.moyenne_generale is not None else float('-inf')
        mga = getattr(e, 'moyenne_generale_annuelle', None)
        return mga if mga is not None else mg

    evaluations_list = list(evaluations)
    annees = (Evaluation.objects
              .values_list('annee', flat=True)
              .distinct().order_by('-annee'))

    # Classements par direction
    classements_par_direction = {}
    for direction in directions:
        ev_dir = [e for e in evaluations_list if e.agent.direction == direction]
        s1 = sorted([e for e in ev_dir if e.semestre == 1], key=_key_moy, reverse=True)
        s2 = sorted([e for e in ev_dir if e.semestre == 2], key=_key_annuelle, reverse=True)
        classements_par_direction[direction] = {'s1': s1, 's2': s2}

    classement_general_s1 = sorted((e for e in evaluations_list if e.semestre == 1), key=_key_moy, reverse=True)
    classement_general_s2 = sorted((e for e in evaluations_list if e.semestre == 2), key=_key_annuelle, reverse=True)

    # -------- Section "Évaluer Directeur" (si tu la gardes) --------
    directeurs = Utilisateur.objects.filter(role='directeur')

    # ADAPTE ce lien selon ton modèle : Agent.utilisateur (ou Agent.user)
    agents = Agent.objects.filter(utilisateur__in=directeurs).select_related('direction')
    user_to_agent = {a.utilisateur_id: a for a in agents}  # si c’est Agent.user : {a.user_id: a for a in agents}

    directeur_to_agent = {d.id: (user_to_agent[d.id].id if d.id in user_to_agent else None) for d in directeurs}

    evaluations_data_responsables = {}
    for d in directeurs:
        agent = user_to_agent.get(d.id)
        if agent is not None:
            s1 = Evaluation.objects.filter(agent=agent, semestre=1).order_by('-annee').first()
            s2 = Evaluation.objects.filter(agent=agent, semestre=2).order_by('-annee').first()
        else:
            s1 = s2 = None
        evaluations_data_responsables[d.id] = {'s1': s1, 's2': s2}

    eval_form = EvaluationForm()
    directeurs_agents_ids = {d.id: (user_to_agent[d.id].id if d.id in user_to_agent else None) for d in directeurs}

    # -------- Contexte --------
    return render(request, "fiches/dashboard_dg.html", {
        "directions": directions,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,

        # Onglet Liste (signé Directeur)
        "evaluations": evaluations,

        # Onglet À signer (décision posée, signé Directeur, pas signé DG)
        "evaluations_a_signer": evaluations_a_signer,

        # Classements
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": classement_general_s1,
        "classement_general_s2": classement_general_s2,

        # Section évaluer directeur (si utilisée dans ton template)
        "directeurs": directeurs,
        "evaluations_data_responsables": evaluations_data_responsables,
        "eval_form": eval_form,
        "directeur_to_agent": directeur_to_agent,
        "directeurs_agents_ids": directeurs_agents_ids,
    })'''

@login_required
def dashboard_dg(request):
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # -------- Filtres formulaire --------
    directions       = Direction.objects.all()
    direction_filter = request.GET.get('direction', 'all')
    annee_filter     = request.GET.get('annee', '')
    semestre_filter  = request.GET.get('semestre', '')

    # -------- Base queryset --------
    # Pour les agents/responsables normaux : doit être signé par le directeur
    # Pour les directeurs : pas besoin de signature du directeur (car évalués directement par le DG)
    from django.db.models import Q

    base_qs = Evaluation.objects.filter(
        Q(est_signe_directeur=True) | Q(agent__utilisateur__role='directeur'),  # Inclure les directeurs même si pas signé par directeur
        moyenne_generale__isnull=False
    ).exclude(
        moyenne_generale=0
    ).select_related('agent', 'agent__direction', 'agent__utilisateur')

    # Appliquer les filtres
    if direction_filter and direction_filter != 'all':
        try:
            base_qs = base_qs.filter(agent__direction_id=int(direction_filter))
        except ValueError:
            pass
    if annee_filter:
        try:
            base_qs = base_qs.filter(annee=int(annee_filter))
        except ValueError:
            pass
    if semestre_filter:
        try:
            base_qs = base_qs.filter(semestre=int(semestre_filter))
        except ValueError:
            pass

    # -------- Évaluations --------
    evaluations = base_qs.order_by('-annee', '-semestre', 'agent__nom', 'agent__prenoms')
    evaluations_agents = evaluations.filter(agent__type_personnel='agent')

    # Séparer les responsables et les directeurs
    evaluations_responsables = evaluations.filter(
        agent__type_personnel='responsable'
    ).exclude(
        agent__utilisateur__role='directeur'  # Exclure les directeurs des responsables
    )

    evaluations_directeurs = evaluations.filter(
        agent__utilisateur__role='directeur'
    )

    # -------- Évaluations à signer --------
    evaluations_a_signer = base_qs.filter(
        est_signe_dg=False,
        decision_finale__isnull=False
    ).exclude(
        decision_finale=''
    ).order_by('-annee', '-semestre')

    nombre_a_signer = evaluations_a_signer.count()

    # -------- Fonction pour marquer signed_by_evaluator --------
    def _mark_signed_by_evaluator(qs):
        result = []
        for e in qs:
            is_dir = getattr(getattr(e.agent, 'utilisateur', None), 'role', None) == 'directeur'
            e.signed_by_evaluator = e.est_signe_agent if is_dir else e.est_signe_directeur
            result.append(e)
        return result

    evaluations_list = _mark_signed_by_evaluator(list(evaluations))
    evaluations_a_signer_list = _mark_signed_by_evaluator(list(evaluations_a_signer))

    # -------- Années disponibles --------
    annees = (
        Evaluation.objects
        .filter(est_signe_directeur=True)
        .values_list('annee', flat=True)
        .distinct()
        .order_by('-annee')
    )

    # ✅ CORRECTION ICI : Définir les semestres directement
    semestres = [(1, 'Semestre 1'), (2, 'Semestre 2')]

    # -------- Clés de tri --------
    def _key_moy(e):
        return e.moyenne_generale if e.moyenne_generale is not None else float('-inf')

    def _key_annuelle(e):
        mg = e.moyenne_generale if e.moyenne_generale is not None else float('-inf')
        if hasattr(e, 'moyenne_generale_annuelle'):
            mga = e.moyenne_generale_annuelle
            return mga if mga is not None else mg
        return mg

    # -------- Classements par direction --------
    classements_par_direction = {}
    for direction in directions:
        ev_dir = [e for e in evaluations_list if e.agent.direction == direction]
        s1 = sorted([e for e in ev_dir if e.semestre == 1], key=_key_moy, reverse=True)
        s2 = sorted([e for e in ev_dir if e.semestre == 2], key=_key_annuelle, reverse=True)
        classements_par_direction[direction] = {'s1': s1, 's2': s2}

    classement_general_s1 = sorted(
        (e for e in evaluations_list if e.semestre == 1),
        key=_key_moy,
        reverse=True
    )
    classement_general_s2 = sorted(
        (e for e in evaluations_list if e.semestre == 2),
        key=_key_annuelle,
        reverse=True
    )

    # -------- Section "Évaluer Directeur" --------
    directeurs = Utilisateur.objects.filter(role='directeur')
    agents = Agent.objects.filter(utilisateur__in=directeurs).select_related('direction', 'utilisateur')
    user_to_agent = {a.utilisateur_id: a for a in agents}

    directeurs_agents_ids = {
        d.id: (user_to_agent[d.id].id if d.id in user_to_agent else None)
        for d in directeurs
    }

    # Dans votre vue dashboard_dg
    evaluations_avec_avis = Evaluation.objects.filter(
        avis_agent__isnull=False
    ).exclude(avis_agent='')

    evaluations_data_responsables = {}
    for d in directeurs:
        agent = user_to_agent.get(d.id)
        if agent:
            s1 = Evaluation.objects.filter(agent=agent, semestre=1).order_by('-annee').first()
            s2 = Evaluation.objects.filter(agent=agent, semestre=2).order_by('-annee').first()
        else:
            s1 = s2 = None
        evaluations_data_responsables[d.id] = {'s1': s1, 's2': s2}

    eval_form = EvaluationForm()

    # Récupérer la période d'évaluation active
    periode_active = PeriodeEvaluation.objects.filter(active=True).first()

    # -------- Contexte --------
    return render(request, "fiches/dashboard_dg.html", {
        "directions": directions,
        "direction_filter": direction_filter,
        "annee_filter": annee_filter,
        "semestre_filter": semestre_filter,
        "annees": annees,
        "semestres": semestres,  # ✅ Maintenant défini correctement
        "evaluations": evaluations_list,
        "evaluations_agents": evaluations_agents,
        "evaluations_responsables": evaluations_responsables,
        "evaluations_directeurs": evaluations_directeurs,
        "evaluations_a_signer": evaluations_a_signer_list,
        "nombre_a_signer": nombre_a_signer,
        "classements_par_direction": classements_par_direction.items(),
        "classement_general_s1": classement_general_s1,
        "classement_general_s2": classement_general_s2,
        "evaluations_avec_avis" : evaluations_avec_avis,
        "directeurs": directeurs,
        "evaluations_data_responsables": evaluations_data_responsables,
        "eval_form": eval_form,
        "directeurs_agents_ids": directeurs_agents_ids,
        "user_to_agent": user_to_agent,
        "periode_active": periode_active,
    })



# fiches/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from .models import Evaluation, UserProfile  # adapte l'import si UserProfile est ailleurs

@login_required
def signer_evaluation_dg(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # 1) Vérifs d'accès/état
    if not hasattr(request.user, "is_directeur_general") or not request.user.is_directeur_general():
        messages.error(request, "Accès refusé : seul le Directeur Général peut signer.")
        return redirect("dashboard_dg")

    '''if not evaluation.est_signe_directeur:
        messages.warning(request, "⛔ Cette évaluation doit d’abord être signée par le Directeur.")
        return redirect("dashboard_dg")'''

    # Doit avoir au moins 1 décision
    has_decision = False
    if evaluation.decision_finale is None:
        has_decision = False
    elif isinstance(evaluation.decision_finale, (list, tuple)):
        has_decision = len(evaluation.decision_finale) > 0
    else:
        # si c'est une chaîne (ex: 'formation' ou 'formation,promotion')
        has_decision = str(evaluation.decision_finale).strip() != ""

    if not has_decision:
        messages.warning(request, "⛔ Veuillez renseigner au moins une décision avant la signature du DG.")
        return redirect("dashboard_dg")

    # 2) POST = signature
    if request.method == "POST":
        evaluation.est_signe_dg = True
        evaluation.date_signature_dg = timezone.now()
        evaluation.utilisateur_signature_dg = request.user  # pour tracer qui a signé

        # Optionnel : stocker l'image de signature sur l'évaluation (si champ File/ImageField prévu)
        try:
            profile_dg = UserProfile.objects.filter(user=request.user).first()
        except UserProfile.DoesNotExist:
            profile_dg = None

        if hasattr(evaluation, "signature_dg"):
            # si tu as un champ ImageField/FileField signature_dg sur Evaluation
            if profile_dg and getattr(profile_dg, "signature", None) and not evaluation.signature_dg:
                evaluation.signature_dg = profile_dg.signature  # référence le même fichier

        evaluation.save()
        messages.success(request, "✅ Évaluation signée par le Directeur Général.")
        return redirect("dashboard_dg")

    # 3) GET = page de confirmation
    return render(request, "fiches/signer_evaluation_dg.html", {
        "evaluation": evaluation
    })




from django.conf import settings
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    template_name = 'fiches/login.html'

    def form_valid(self, form):
        user = form.get_user()
        is_default = user.check_password(settings.DEFAULT_PASSWORD)
        is_agent   = getattr(user, 'role', None) == 'agent'  # ou .profile.role

        # on fait le login (met à jour last_login)
        super().form_valid(form)

        # si c'est un agent ET qu'il est toujours sur le mot de passe par défaut
        if is_agent and is_default:
            return redirect('modifier_mot_de_passe')

        # sinon on le redirige vers son propre dashboard selon son rôle
        if user.role == 'directeur':
            return redirect('dashboard_directeur')
        if user.role == 'rh':
            return redirect('dashboard_rh')
        if user.role == 'dg':
            return redirect('dashboard_dg')
        # rôle « agent » sans mot de passe par défaut
        return redirect('dashboard_agent')

'''
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from .models import PeriodeEvaluation
from .forms  import PeriodeEvaluationForm

def is_rh(user):
    return user.is_authenticated and user.is_rh()

@user_passes_test(is_rh)
def gerer_periodes(request, pk=None):
    """
    Si pk est fourni, on charge l'instance pour modification,
    sinon on crée une nouvelle période.
    """
    periodes = PeriodeEvaluation.objects.all()
    instance = None

    if pk:
        instance = get_object_or_404(PeriodeEvaluation, pk=pk)

    if request.method == "POST":
        form = PeriodeEvaluationForm(request.POST, instance=instance)
        if form.is_valid():
            # Si on active, désactivez les autres
            if form.cleaned_data["active"]:
                PeriodeEvaluation.objects.update(active=False)
            form.save()
            action = "modifiée" if instance else "créée"
            messages.success(request, f"✅ Période {action} avec succès.")
            return redirect('gerer_periodes')
        else:
            messages.error(request, "⚠️ Erreurs dans le formulaire.")
    else:
        form = PeriodeEvaluationForm(instance=instance)

    return render(request, "fiches/gerer_periodes.html", {
        "periodes": periodes,
        "form": form,
        "editing": bool(instance),
        "editing_pk": pk,
    })
'''


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from .models import PeriodeEvaluation
from .forms  import PeriodeEvaluationForm

def is_rh(user):
    return user.is_authenticated and user.is_rh()

@user_passes_test(is_rh)
def gerer_periodes(request):
    """Page LISTE uniquement (pas de formulaire ici)."""
    periodes = PeriodeEvaluation.objects.order_by("-annee", "-semestre")
    return render(request, "fiches/periodes_liste.html", {"periodes": periodes})

@user_passes_test(is_rh)
def ajouter_periode(request):
    """Page d’AJOUT dédiée."""
    if request.method == "POST":
        form = PeriodeEvaluationForm(request.POST)
        if form.is_valid():
            # si on active cette période, désactiver les autres
            if form.cleaned_data.get("active"):
                PeriodeEvaluation.objects.update(active=False)
            form.save()
            messages.success(request, "✅ Période créée avec succès.")
            return redirect("gerer_periodes")
        messages.error(request, "⚠️ Erreurs dans le formulaire.")
    else:
        form = PeriodeEvaluationForm()
    return render(request, "fiches/periode_form.html", {
        "form": form,
        "editing": False,
        "title": "Enregistrer une période",
        "submit_label": "Enregistrer",
    })

@user_passes_test(is_rh)
def modifier_periode(request, pk):
    """Page de MODIFICATION dédiée."""
    instance = get_object_or_404(PeriodeEvaluation, pk=pk)
    if request.method == "POST":
        form = PeriodeEvaluationForm(request.POST, instance=instance)
        if form.is_valid():
            if form.cleaned_data.get("active"):
                PeriodeEvaluation.objects.exclude(pk=instance.pk).update(active=False)
            form.save()
            messages.success(request, "✅ Période modifiée avec succès.")
            return redirect("gerer_periodes")
        messages.error(request, "⚠️ Erreurs dans le formulaire.")
    else:
        form = PeriodeEvaluationForm(instance=instance)
    return render(request, "fiches/periode_form.html", {
        "form": form,
        "editing": True,
        "title": "Modifier la période",
        "submit_label": "Mettre à jour",
    })


from django.shortcuts           import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models          import Count

from .models import Agent, Evaluation, Direction

def is_rh_or_directeur_general(user):
    return user.is_authenticated and (user.is_rh() or user.is_directeur_general())

@login_required
@user_passes_test(is_rh_or_directeur_general)
def dashboard_stats(request):
    stats = []
    for direction in Direction.objects.all().order_by('nom'):
        total_agents = Agent.objects.filter(direction=direction).count()
        evaluated_agents = (
            Evaluation.objects
                      .filter(est_signe_agent=True, agent__direction=direction)
                      .values('agent')
                      .distinct()
                      .count()
        )
        percent = int(evaluated_agents * 100 / total_agents) if total_agents else 0
        stats.append({
            'name': direction.nom,
            'evaluated': evaluated_agents,
            'total': total_agents,
            'percent': percent,
        })

    return render(request, 'fiches/dashboard_stats.html', {
        'stats': stats,
    })


# views.py
import io
from django.http import HttpResponse
from django.db.models import Count

import matplotlib      # <- Agg forcé ici
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .models import Agent, Evaluation

def chart_agents(request):
    data = (
        Agent.objects
             .values('direction__nom')
             .annotate(total=Count('id'))
             .order_by('direction__nom')
    )
    # Si direction__nom est None, on remplace par 'Sans direction'
    labels = [
        d['direction__nom'] if d['direction__nom'] is not None else 'Sans direction'
        for d in data
    ]
    counts = [d['total'] for d in data]

    plt.figure(figsize=(8,4))
    plt.bar(labels, counts)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/png')


def chart_evalues(request):
    data = (
        Evaluation.objects
                  .filter(est_signe_agent=True)
                  .values('agent__direction__nom')
                  .annotate(total=Count('agent', distinct=True))
                  .order_by('agent__direction__nom')
    )
    labels = [
        d['agent__direction__nom'] if d['agent__direction__nom'] is not None else 'Sans direction'
        for d in data
    ]
    counts = [d['total'] for d in data]

    plt.figure(figsize=(8,4))
    plt.bar(labels, counts)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/png')

'''
# fiches/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Agent, Evaluation, SousDirection, UserProfile, PeriodeEvaluation

def is_sous_directeur(user):
    return user.role == 'sous_directeur'

@login_required
@user_passes_test(is_sous_directeur)
def dashboard_sous_directeur(request):
    # 1) Récupérer la SousDirection liée à l'utilisateur
    try:
        sd = request.user.sous_direction
    except AttributeError:
        messages.error(request, "Accès refusé. Vous n'êtes rattaché à aucune Sous-direction.")
        return render(request, 'fiches/erreur.html', {
            'message': "Accès refusé. Vous n'êtes rattaché à aucune Sous-direction."
        })

    # 2) Récupérer la période d'évaluation active
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ Aucune période d’évaluation active. Contactez le service RH.")
        return redirect('login')


    # 3) Récupérer tous les agents et responsables de cette SousDirection
    agents = Agent.objects.filter(
        type_personnel='agent',
        sous_direction=sd
    ).exclude(utilisateur=request.user)
    responsables = Agent.objects.filter(
        type_personnel='responsable',
        sous_direction=sd
    ).exclude(utilisateur=request.user)

    # Récupérer les évaluations existantes et extraire les IDs
    evaluations = Evaluation.objects.filter(agent__in=agents, annee=periode.annee, semestre=periode.semestre)
    completed_ids = [ev.agent.id for ev in evaluations]

    selected_service = (request.GET.get('service') or '').strip() or None

    # 4) Lister les services existants pour le filtre (noms uniques, non nuls)
    services = (
        Agent.objects
        .filter(type_personnel__in=['agent', 'responsable'], sous_direction=sd)
        .exclude(utilisateur=request.user)
        .exclude(service__isnull=True)
        .values('service__id', 'service__nom')  # Récupérer id et nom
        .distinct()
        .order_by('service__nom')
    )


    # 5) Appliquer le filtre "service" si présent
    if selected_service:
        agents = agents.filter(service__id=selected_service)
        responsables = responsables.filter(service__id=selected_service)

    # 6) Récupérer et organiser les évaluations pour agents + responsables
    personnes = list(agents) + list(responsables)
    evaluations = Evaluation.objects.filter(agent__in=personnes, annee=periode.annee, semestre=periode.semestre)


    # 7) Profil pour signature si besoin
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # 8) Rendu du template
    return render(request, 'fiches/dashboard_sousdirecteur.html', {
        'periode': periode,
        'periode_active': periode,  # Alias pour cohérence avec dashboard_directeur
        'agents': agents,
        'responsables': responsables,
        'services': services,
        'completed_ids': completed_ids,
        'selected_service': selected_service,
        #'evaluations_data': evaluations_data,
        'profile': profile,
    })'''

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Agent, Evaluation, SousDirection, UserProfile, PeriodeEvaluation


def is_sous_directeur(user):
    return user.role == 'sous_directeur'


@login_required
@user_passes_test(is_sous_directeur)
def dashboard_sous_directeur(request):
    # 1) Récupérer la SousDirection liée à l'utilisateur
    try:
        sd = request.user.sous_direction
    except AttributeError:
        messages.error(request, "Accès refusé. Vous n'êtes rattaché à aucune Sous-direction.")
        return render(request, 'fiches/erreur.html', {
            'message': "Accès refusé. Vous n'êtes rattaché à aucune Sous-direction."
        })

    # 2) Récupérer la période d'évaluation active
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ Aucune période d'évaluation active. Contactez le service RH.")
        return redirect('login')

    # 3) Récupérer tous les agents et responsables de cette SousDirection
    agents = Agent.objects.filter(
        type_personnel='agent',
        sous_direction=sd
    ).exclude(utilisateur=request.user)

    responsables = Agent.objects.filter(
        type_personnel='responsable',
        sous_direction=sd
    ).exclude(utilisateur=request.user)

    # 4) Récupérer le filtre de service sélectionné
    selected_service = (request.GET.get('service') or '').strip() or None

    # 5) Lister les services existants pour le filtre (noms uniques, non nuls)
    services = (
        Agent.objects
        .filter(type_personnel__in=['agent', 'responsable'], sous_direction=sd)
        .exclude(utilisateur=request.user)
        .exclude(service__isnull=True)
        .values('service__id', 'service__nom')
        .distinct()
        .order_by('service__nom')
    )

    # 6) Appliquer le filtre "service" si présent
    if selected_service:
        agents = agents.filter(service__id=selected_service)
        responsables = responsables.filter(service__id=selected_service)

    # 7) Organiser les évaluations par agent et par semestre
    evaluations = Evaluation.objects.filter(
        agent__in=list(agents) + list(responsables)
    ).select_related('agent')

    evaluations_data = {}
    for agent in agents:
        agent_evals = evaluations.filter(agent=agent)
        evaluations_data[agent.id] = {
            's1': None,
            's2': None,
        }
        for eval in agent_evals:
            if eval.semestre == 1:
                evaluations_data[agent.id]['s1'] = eval
            elif eval.semestre == 2:
                evaluations_data[agent.id]['s2'] = eval

    evaluations_data_responsables = {}
    for responsable in responsables:
        responsable_evals = evaluations.filter(agent=responsable)
        evaluations_data_responsables[responsable.id] = {
            's1': None,
            's2': None,
        }
        for eval in responsable_evals:
            if eval.semestre == 1:
                evaluations_data_responsables[responsable.id]['s1'] = eval
            elif eval.semestre == 2:
                evaluations_data_responsables[responsable.id]['s2'] = eval

    # 8) Profil pour signature si besoin
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # 9) Rendu du template
    return render(request, 'fiches/dashboard_sousdirecteur.html', {
        'periode': periode,
        'periode_active': periode,  # Alias pour cohérence avec dashboard_directeur
        'agents': agents,
        'responsables': responsables,
        'services': services,
        'evaluations_data': evaluations_data,
        'evaluations_data_responsables': evaluations_data_responsables,
        'selected_service': selected_service,
        'profile': profile,
    })

# fiches/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import Agent, Evaluation, PeriodeEvaluation, JustificationNote
from .forms import EvaluationFormSousDirecteur

CRITERES_BASE = [
    {'nom': 'connaissances_sous_directeur',      'label': 'Connaissances et aptitudes professionnelles'},
    {'nom': 'initiative_sous_directeur',         'label': "Esprit d'initiative"},
    {'nom': 'rendement_sous_directeur',          'label': 'Puissance du travail et rendement'},
    {'nom': 'respect_objectifs_sous_directeur',  'label': 'Respect des objectifs'},
    {'nom': 'civisme_sous_directeur',            'label': 'Civisme'},
    {'nom': 'service_public_sous_directeur',     'label': 'Sens du service public'},
    {'nom': 'relations_humaines_sous_directeur', 'label': 'Relations humaines'},
    {'nom': 'discipline_sous_directeur',         'label': "Esprit de discipline"},
    {'nom': 'ponctualite_sous_directeur',        'label': 'Ponctualité'},
    {'nom': 'assiduite_sous_directeur',          'label': 'Assiduité'},
    {'nom': 'tenue_sous_directeur',              'label': 'Tenue'},
]
CRITERES_MANAGEMENT = [
    {'nom': 'leadership_sous_directeur',         'label': 'Leadership'},
    {'nom': 'planification_sous_directeur',      'label': 'Planification'},
    {'nom': 'travail_equipe_sous_directeur',     'label': "Travail d'équipe"},
    {'nom': 'resolution_problemes_sous_directeur','label': 'Résolution de problèmes'},
    {'nom': 'prise_decision_sous_directeur',     'label': 'Prise de décision'},
]
CRITERES_BASE_CS = [
    {'nom': 'connaissances_chef_service',      'label': 'Connaissances et aptitudes professionnelles'},
    {'nom': 'initiative_chef_service',         'label': "Esprit d'initiative"},
    {'nom': 'rendement_chef_service',          'label': 'Puissance du travail et rendement'},
    {'nom': 'respect_objectifs_chef_service',  'label': 'Respect des objectifs'},
    {'nom': 'civisme_chef_service',            'label': 'Civisme'},
    {'nom': 'service_public_chef_service',     'label': 'Sens du service public'},
    {'nom': 'relations_humaines_chef_service', 'label': 'Relations humaines'},
    {'nom': 'discipline_chef_service',         'label': 'Esprit de discipline'},
    {'nom': 'ponctualite_chef_service',        'label': 'Ponctualité'},
    {'nom': 'assiduite_chef_service',          'label': 'Assiduité'},
    {'nom': 'tenue_chef_service',              'label': 'Tenue'},
]

def get_criteres_affichage(agent):
    criteres = CRITERES_BASE.copy()
    if getattr(agent, 'type_personnel','') == 'responsable':
        criteres += CRITERES_MANAGEMENT
    return criteres
@login_required
@user_passes_test(lambda u: getattr(u,'role','')=='sous_directeur')
def evaluer_agent_sous_directeur(request, agent_id):
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode or today < periode.date_debut or today > periode.date_fin:
        messages.warning(request,
            f"🔒 Période d’évaluation : {periode.date_debut} → {periode.date_fin}")
        return redirect('dashboard_sous_directeur')

    agent      = get_object_or_404(Agent, id=agent_id)
    evaluation = Evaluation.objects.filter(
        agent=agent,
        annee=periode.annee,
        semestre=periode.semestre
    ).first()

    # Notes et justif CS
    note_cs_map = {
        crit['nom']: getattr(evaluation, crit['nom'], None)
        for crit in CRITERES_BASE_CS
    }
    justif_cs_map = {
        j.critere: j.justification
        for j in JustificationNote.objects.filter(
            evaluation=evaluation,
            critere__in=[c['nom'] for c in CRITERES_BASE_CS]
        )
    }

    # POST SD
    if request.method=='POST':
        form = EvaluationFormSousDirecteur(request.POST, instance=evaluation)
        # …
        if form.is_valid():
            try:
                with transaction.atomic():
                    ev = form.save(commit=False)
                    ev.agent = agent
                    ev.annee = periode.annee
                    ev.semestre = periode.semestre
                    ev.type_personnel = agent.type_personnel
                    ev.save()

                    # stocker justifs SD non vides _avec_ la note correspondante_
                    criteres_sd = get_criteres_affichage(agent)
                    for crit in criteres_sd:
                        t = request.POST.get(f"{crit['nom']}_justif", "").strip()
                        n = request.POST.get(crit['nom'])  # note SD en string
                        if t and n:
                            JustificationNote.objects.update_or_create(
                                evaluation=ev,
                                critere=crit['nom'],
                                defaults={
                                    'justification': t,
                                    'note': int(n),  # ici on fournit la note SD
                                }
                            )
                messages.success(request, "✅ Évaluation enregistrée.")
                return redirect('dashboard_sous_directeur')
            except Exception as e:
                messages.error(request, f"⚠️ Erreur en sauvegarde : {e}")
    else:
        form = (EvaluationFormSousDirecteur(instance=evaluation)
                if evaluation else
                EvaluationFormSousDirecteur(initial={
                    'annee': periode.annee,
                    'semestre': periode.semestre,
                    'type_personnel': agent.type_personnel
                }))

    # Préparer les justifs SD avec le bon attribut
    criteres_sd = get_criteres_affichage(agent)
    justifs_sd = {
        j.critere: j.justification
        for j in JustificationNote.objects.filter(
            evaluation=evaluation,
            critere__in=[c['nom'] for c in criteres_sd]
        )
    }

    # Construit la liste de tuples (bf, label, just_sd, note_cs, just_cs)
    champs = []
    for crit in criteres_sd:
        nom_sd  = crit['nom']
        bf      = form[nom_sd]
        label   = crit['label']
        just_sd = justifs_sd.get(nom_sd, '')
        nom_cs  = nom_sd.replace('_sous_directeur','_chef_service')
        note_cs = note_cs_map.get(nom_cs)
        just_cs = justif_cs_map.get(nom_cs, '')
        champs.append((bf, label, just_sd, note_cs, just_cs))

    champs_rendement    = champs[:4]
    champs_comportement = champs[4:len(CRITERES_BASE)]
    champs_management   = champs[len(CRITERES_BASE):]

    return render(request, 'fiches/evaluer_agent_sous_directeur.html', {
        'form': form,
        'agent': agent,
        'semestre': periode.semestre,
        'champs_rendement':    champs_rendement,
        'champs_comportement': champs_comportement,
        'champs_management':   champs_management,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from .models import Agent, Evaluation, PeriodeEvaluation, UserProfile

# Vérification du rôle chef de service

def is_chef_service(user):
    return getattr(user, 'role', '') == 'chef_service'

# Dashboard pour le chef de service
@login_required
@user_passes_test(is_chef_service)
def dashboard_chef_service(request):
    # Récupérer le service lié à l'utilisateur
    try:
        service = request.user.service
    except AttributeError:
        messages.error(request, "Accès refusé. Vous n'êtes rattaché à aucun service.")
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes rattaché à aucun service."})

    # Période d'évaluation active
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ Aucune période d’évaluation active. Contactez le service RH.")
        return redirect('login')

    # Liste des agents de ce service
    agents = Agent.objects.filter(type_personnel='agent', service=service)

    # Organiser les évaluations par agent et par semestre
    evaluations = Evaluation.objects.filter(agent__in=agents).select_related('agent')

    evaluations_data = {}
    for agent in agents:
        agent_evals = evaluations.filter(agent=agent)
        evaluations_data[agent.id] = {
            's1': None,
            's2': None,
        }
        for eval in agent_evals:
            if eval.semestre == 1:
                evaluations_data[agent.id]['s1'] = eval
            elif eval.semestre == 2:
                evaluations_data[agent.id]['s2'] = eval

    # Profil pour signature
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Rendu du template
    return render(request, 'fiches/dashboard_chef_service.html', {
        'periode': periode,
        'periode_active': periode,  # Alias pour cohérence avec dashboard_directeur
        'service': service,
        'agents': agents,
        'evaluations_data': evaluations_data,
        'profile': profile,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import Agent, Evaluation, PeriodeEvaluation, JustificationNote
from .forms import EvaluationFormChefService

# Critères spécifiques au chef de service
CRITERES_BASE_CS = [
    {'nom': 'connaissances_chef_service', 'label': 'Connaissances et aptitudes professionnelles'},
    {'nom': 'initiative_chef_service', 'label': 'Esprit d\'initiative'},
    {'nom': 'rendement_chef_service', 'label': 'Puissance du travail et rendement'},
    {'nom': 'respect_objectifs_chef_service', 'label': 'Respect des objectifs'},
    {'nom': 'civisme_chef_service', 'label': 'Civisme'},
    {'nom': 'service_public_chef_service', 'label': 'Sens du service public'},
    {'nom': 'relations_humaines_chef_service', 'label': 'Relations humaines'},
    {'nom': 'discipline_chef_service', 'label': 'Esprit de discipline'},
    {'nom': 'ponctualite_chef_service', 'label': 'Ponctualité'},
    {'nom': 'assiduite_chef_service', 'label': 'Assiduité'},
    {'nom': 'tenue_chef_service', 'label': 'Tenue'},
]

CRITERES_MANAGEMENT_CS = [
    {'nom': 'leadership', 'label': 'Leadership'},
    {'nom': 'planification', 'label': 'Planification'},
    {'nom': 'travail_equipe', 'label': 'Travail en équipe'},
    {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
    {'nom': 'prise_decision', 'label': 'Prise de décision'},
]

# Helpers pour préparer les données

def get_criteres_affichage_cs(agent):
    """
    Retourne la liste des critères pour un chef de service.
    Ajoute CRITERES_MANAGEMENT_CS si agent.type_personnel == 'chef_service'.
    """
    criteres = CRITERES_BASE_CS.copy()
    if getattr(agent, 'type_personnel', '') == 'chef_service':
        criteres += CRITERES_MANAGEMENT_CS
    return criteres


def get_justifications_existantes_cs(evaluation):
    """
    Récupère les justifications existantes pour l'évaluation du chef de service.
    Renvoie un dict critere -> (note, texte)
    """
    justifs = {}
    if evaluation:
        for j in JustificationNote.objects.filter(evaluation=evaluation):
            justifs[j.critere] = (j.note, j.justification)
    return justifs


def sauvegarder_justifications_cs(evaluation, criteres, post_data):
    """
    Pour un chef de service, on ne stocke que les justifications non-vides.
    On supprime d'abord toutes les anciennes entrées CS pour cet evaluation,
    puis on recrée uniquement celles pour lesquelles un texte a été fourni.
    """
    # 1) Suppression
    noms_cs = [c['nom'] for c in criteres]
    JustificationNote.objects.filter(
        evaluation=evaluation,
        critere__in=noms_cs
    ).delete()

    # 2) Recréation des seules justifs non-vides
    for crit in criteres:
        name = crit['nom']
        texte = post_data.get(f"{name}_justif", "").strip()
        if not texte:
            continue  # on n'enregistre pas les justifications vides

        # Récupérer et convertir la note (s'il y en a une)
        try:
            note_int = int(post_data.get(name))
        except (TypeError, ValueError):
            continue

        # Création
        JustificationNote.objects.create(
            evaluation=evaluation,
            critere=name,
            note=note_int,
            justification=texte
        )

@login_required
@user_passes_test(lambda u: u.role == 'chef_service')
def evaluer_agent_chef_service(request, agent_id):
    """
    Permet au chef de service d'évaluer uniquement les agents.
    Les responsables ne peuvent pas être évalués ici.
    """
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode or today < periode.date_debut or today > periode.date_fin:
        messages.error(request, "⚠️ Période d'évaluation non valide.")
        return redirect('dashboard_chef_service')

    agent = get_object_or_404(Agent, id=agent_id)
    if agent.type_personnel != 'agent':
        messages.error(request, "⚠️ Vous ne pouvez évaluer que les agents.")
        return redirect('dashboard_chef_service')

    evaluation = Evaluation.objects.filter(
        agent=agent,
        annee=periode.annee,
        semestre=periode.semestre
    ).first()

    criteres = get_criteres_affichage_cs(agent)
    justifs_cs = get_justifications_existantes_cs(evaluation)

    if request.method == 'POST':
        form = EvaluationFormChefService(request.POST, instance=evaluation)
        if form.is_valid():
            try:
                with transaction.atomic():
                    evaluation = form.save(commit=False)
                    evaluation.agent = agent
                    evaluation.annee = periode.annee
                    evaluation.semestre = periode.semestre
                    evaluation.type_personnel = agent.type_personnel
                    evaluation.save()
                    sauvegarder_justifications_cs(evaluation, criteres, request.POST)
                messages.success(request, '✅ Évaluation enregistrée.')
                return redirect('dashboard_chef_service')
            except Exception as e:
                messages.error(request, f'⚠️ Erreur en sauvegarde : {e}')
        else:
            messages.error(request, '⚠️ Formulaire invalide.')
    else:
        form = EvaluationFormChefService(instance=evaluation) if evaluation else EvaluationFormChefService(
            initial={
                'annee': periode.annee,
                'semestre': periode.semestre,
                'type_personnel': agent.type_personnel
            }
        )

    # Préparer les champs pour affichage (BoundFields + justifs)
    justifs_data = {crit: justifs_cs.get(crit, (None, '')) for crit in [c['nom'] for c in criteres]}
    champs = []
    for crit in criteres:
        bf = form[crit['nom']]
        note_cs, txt_cs = justifs_data.get(crit['nom'], (None, ''))
        champs.append((bf, crit['label'], note_cs, txt_cs))

    # Segmentation par sections
    nb_rend = 4
    champs_rendement    = champs[:nb_rend]
    champs_comportement = champs[nb_rend:len(CRITERES_BASE_CS)]
    champs_management   = champs[len(CRITERES_BASE_CS):]

    return render(request,
        'fiches/evaluer_agent_chef_service.html',
        {
          'form': form,
          'agent': agent,
          'semestre': periode.semestre,
          'champs_rendement': champs_rendement,
          'champs_comportement': champs_comportement,
          'champs_management': champs_management,
          'criteres': criteres,
          'justifs_cs': justifs_cs,
        }
    )
from datetime import datetime
from django.shortcuts               import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib                import messages
from django.utils                  import timezone

from .models   import Agent, Evaluation, PeriodeEvaluation, JustificationNote
from .forms    import EvaluationFormSousDirecteur

# 🚩 Votre liste de critères
CRIT_FIELDS = [
    {'nom': 'connaissances_sous_directeur',      'label': 'Connaissances et aptitudes professionnelles'},
    {'nom': 'initiative_sous_directeur',         'label': "Esprit d'initiative"},
    {'nom': 'rendement_sous_directeur',          'label': 'Puissance du travail et rendement'},
    {'nom': 'respect_objectifs_sous_directeur',  'label': 'Respect des objectifs'},
    {'nom': 'civisme_sous_directeur',            'label': 'Civisme'},
    {'nom': 'service_public_sous_directeur',     'label': 'Sens du service public'},
    {'nom': 'relations_humaines_sous_directeur', 'label': 'Relations humaines'},
    {'nom': 'discipline_sous_directeur',         'label': "Esprit de discipline"},
    {'nom': 'ponctualite_sous_directeur',        'label': 'Ponctualité'},
    {'nom': 'assiduite_sous_directeur',          'label': 'Assiduité'},
    {'nom': 'tenue_sous_directeur',              'label': 'Tenue'},
    {'nom': 'leadership_sous_directeur',         'label': 'Leadership'},
    {'nom': 'planification_sous_directeur',      'label': 'Planification'},
    {'nom': 'travail_equipe_sous_directeur',     'label': "Travail d'équipe"},
    {'nom': 'resolution_problemes_sous_directeur','label': 'Résolution de problèmes'},
    {'nom': 'prise_decision_sous_directeur',     'label': 'Prise de décision'},
]

@login_required
def evaluer_responsable_sous_directeur(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    if agent.type_personnel != 'responsable':
        messages.error(request, "⚠️ Cet utilisateur n'est pas un responsable.")
        return redirect('dashboard_sous_directeur')

    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode or not (periode.date_debut <= today <= periode.date_fin):
        msg = (
            f"🔒 Période du {periode.date_debut:%d/%m/%Y} au {periode.date_fin:%d/%m/%Y}."
            if periode else "⚠️ Aucune période d’évaluation active."
        )
        messages.warning(request, msg)
        return redirect('dashboard_sous_directeur')

    try:
        semestre = int(request.GET.get('semestre', 1))
    except ValueError:
        semestre = 1
    if semestre not in (1, 2):
        semestre = 1

    evaluation = Evaluation.objects.filter(
        agent=agent,
        annee=periode.annee,
        semestre=semestre
    ).first()

    # Récupération des justifs existantes
    justifications = {}
    if evaluation:
        for j in JustificationNote.objects.filter(evaluation=evaluation):
            justifications[j.critere] = j.justification

    initial_data = {
        'annee': periode.annee,
        'semestre': semestre,
        'type_personnel': 'responsable'
    }

    if request.method == "POST":
        form = EvaluationFormSousDirecteur(
            request.POST,
            instance=evaluation,
            initial=initial_data
        )
        if form.is_valid():
            ev = form.save(commit=False)
            ev.agent = agent
            ev.type_personnel = 'responsable'
            ev.save()
            # on purge puis recrée les justifs
            JustificationNote.objects.filter(evaluation=ev).delete()
            for crit in CRIT_FIELDS:
                name = crit['nom']
                note = form.cleaned_data.get(name)
                just = request.POST.get(f"{name}_justif", "").strip()
                if note in (1, 5) and just:
                    JustificationNote.objects.create(
                        evaluation=ev,
                        critere=name,
                        note=note,
                        justification=just
                    )
            messages.success(request, "✅ Évaluation enregistrée avec succès.")
            return redirect('dashboard_sous_directeur')
        else:
            messages.error(request, "⚠️ Formulaire invalide. Merci de vérifier vos saisies.")
    else:
        form = EvaluationFormSousDirecteur(
            instance=evaluation,
            initial=initial_data
        )

    # On construit la liste de champs pour le template
    champs = []
    for crit in CRIT_FIELDS:
        name = crit['nom']
        if name in form.fields:
            champs.append({
                'field':     form[name],
                'label':     crit['label'],
                'justif':    justifications.get(name, "")
            })

    return render(request, 'fiches/evaluer_responsable_sous_directeur.html', {
        'agent':    agent,
        'semestre': semestre,
        'form':     form,
        'champs':   champs,
    })
'''
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .models import Utilisateur, Evaluation, Agent
from .forms import EvaluationForm

@login_required
def evaluer_directeur(request, agent_id):
    # 1) Même contrôle d’accès que le dashboard
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # 2) Récupération agent et directeur associé
    agent = get_object_or_404(Agent, id=agent_id)
    # adapte ce champ selon ton modèle : utilisateur / user
    directeur = get_object_or_404(Utilisateur, id=agent.utilisateur_id, role='directeur')

    # 3) Semestre depuis la querystring (défaut = 1)
    try:
        semestre = int(request.GET.get("semestre", "1") or 1)
    except ValueError:
        semestre = 1

    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            eval_obj = form.save(commit=False)
            # Renseigne les champs obligatoires
            eval_obj.agent = agent
            eval_obj.semestre = semestre
            # si tu as un champ "directeur_user" pour qui évalue / validateur, ajoute-le
            # eval_obj.directeur_user = request.user
            eval_obj.save()
            messages.success(request, f"Évaluation enregistrée pour {directeur.get_full_name()} (S{semestre}).")
            return redirect('dashboard_dg')
    else:
        form = EvaluationForm()

    return render(request, 'fiches/evaluer_directeur_dg.html', {
        'form': form,
        'directeur': directeur,
        'agent': agent,
        'semestre': semestre,
    })

'''
'''
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from .models import Utilisateur, Evaluation
from .forms import EvaluationForm

@login_required
def evaluer_directeur(request, agent_id):
    # 1) Autorisation DG
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # 2) Récupération du “directeur” par ID puis vérification du rôle
    #directeur = get_object_or_404(Utilisateur, id=agent_id)

    agent = get_object_or_404(Agent, id=agent_id)
    evaluation = Evaluation.objects.filter(
        agent=agent,
    ).first()

    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ La période d'évaluation n'est plus ou pas encore active. Contactez le service RH.")
        return redirect('dashboard_dg')

    semestre = int(request.GET.get('semestre', 1))
    if semestre not in [1, 2]:
        semestre = 1

    try:
        evaluation = Evaluation.objects.get(
            agent=agent,
            annee=datetime.now().year,
            semestre=semestre
        )
    except Evaluation.DoesNotExist:
        evaluation = None

    initial_data = {
        'annee': datetime.now().year,
        'semestre': semestre,
        'type_personnel': 'responsable'
    }

    if request.method == "POST":
        print("Données POST :", request.POST)
        form = EvaluationForm(request.POST, instance=evaluation) if evaluation else EvaluationForm(request.POST, initial=initial_data)

        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.agent = agent
            evaluation.semestre = semestre
            evaluation.type_personnel = 'responsable'
            evaluation.save()
            evaluation.calcul_moyennes()

            user_agent = agent.utilisateur  # ou evaluation.agent.utilisateur
            if user_agent.email:
                subject = "Votre évaluation est disponible"
                message = (
                    f"Bonjour {agent.nom} {agent.prenoms},\n\n"
                    f"Votre évaluation du semestre {semestre} de l'année {evaluation.annee} "
                    f"a été réalisée par votre directeur le {timezone.now().strftime('%d/%m/%Y')}.\n\n"
                    "Vous pouvez la consulter depuis votre espace dédié sur le site (evaluation.stats.ci).\n\n"
                    "Cordialement,\n"
                    "Le service RH"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_agent.email],
                        fail_silently=False,
                    )
                    messages.info(request, "✉️ Un email de notification a été envoyé à l'agent.")
                except Exception as e:
                    messages.warning(request, f"⚠️ Impossible d'envoyer l'email : {e}")
            JustificationNote.objects.filter(evaluation=evaluation).delete()
            criteres = [
                {'nom': 'connaissances', 'label': 'Connaissances et aptitudes professionnelles'},
                {'nom': 'initiative', 'label': 'Esprit d\'initiative'},
                {'nom': 'rendement', 'label': 'Puissance du travail et rendement'},
                {'nom': 'respect_objectifs', 'label': 'Respect des objectifs'},
                {'nom': 'civisme', 'label': 'Civisme'},
                {'nom': 'service_public', 'label': 'Sens du service public'},
                {'nom': 'relations_humaines', 'label': 'Relations humaines'},
                {'nom': 'discipline', 'label': 'Esprit de discipline'},
                {'nom': 'ponctualite', 'label': 'Ponctualité'},
                {'nom': 'assiduite', 'label': 'Assiduité'},
                {'nom': 'tenue', 'label': 'Tenue'},
                {'nom': 'leadership', 'label': 'Leadership'},
                {'nom': 'planification', 'label': 'Planification'},
                {'nom': 'travail_equipe', 'label': 'Travail d\'équipe'},
                {'nom': 'resolution_problemes', 'label': 'Résolution de problèmes'},
                {'nom': 'prise_decision', 'label': 'Prise de décision'},
            ]

            for critere in criteres:
                note = request.POST.get(critere['nom'])
                justification = request.POST.get(f"{critere['nom']}_justif", "").strip()
                if note in ['1', '5'] and justification:
                    JustificationNote.objects.create(
                        evaluation=evaluation,
                        critere=critere['nom'],
                        note=int(note),
                        justification=justification
                    )
                    print(f"✅ Justification enregistrée pour {critere['nom']}: {justification}")

            messages.success(request, f"✅ Évaluation du semestre {semestre} enregistrée avec succès.")
            return redirect('dashboard_dg')
        else:
            print("❌ Erreurs du formulaire :", form.errors)
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs et justifications.")


    # Définir les listes de critères pour le template
    criteres_rendement = ['connaissances', 'initiative', 'rendement', 'respect_objectifs']
    criteres_comportement = ['civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualite', 'assiduite', 'tenue']
    criteres_management = ['leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision']

    if request.method == "POST":
        form = EvaluationForm(request.POST)
        if "type_personnel" in form.fields:
            form.fields["type_personnel"].widget = forms.HiddenInput()

        if form.is_valid():
            eval_obj = form.save(commit=False)

            # L’évalué
            if hasattr(eval_obj, "agent"):
                eval_obj.agent = agent
                doublons = Evaluation.objects.filter(agent=agent)
            else:
                eval_obj.evalue = agent
                doublons = Evaluation.objects.filter(evalue=agent)

            # L’évaluateur (si champ)
            if hasattr(eval_obj, "evaleur"):
                eval_obj.evaleur = request.user

            # Forcer le type “responsable”
            if hasattr(eval_obj, "type_personnel"):
                eval_obj.type_personnel = "responsable"

            # Anti-doublon année/semestre
            annee = getattr(eval_obj, "annee", None)
            semestre = getattr(eval_obj, "semestre", None)
            if annee is not None:
                doublons = doublons.filter(annee=annee)
            if semestre is not None:
                doublons = doublons.filter(semestre=semestre)

            if doublons.exists():
                messages.warning(request, "Une évaluation existe déjà pour cette période.")
                return redirect(reverse("dashboard_dg") + "?tab=evaluer-directeur")

            eval_obj.save()
            messages.success(request, f"Évaluation enregistrée pour {agent.get_full_name()}.")
            return redirect(reverse("dashboard_dg") + "?tab=evaluer-directeur")
    else:
        form = EvaluationForm(initial={"type_personnel": "responsable"})
        if "type_personnel" in form.fields:
            form.fields["type_personnel"].widget = forms.HiddenInput()

    return render(request, "fiches/evaluer_directeur_dg.html", {
        "form": form,
        "agent": agent,
        "criteres_rendement": criteres_rendement,
        "criteres_comportement": criteres_comportement,
        "criteres_management": criteres_management,
        "justifications": {},
    })
'''

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime

from .models import Utilisateur, Evaluation, Agent, PeriodeEvaluation, JustificationNote
from .forms import EvaluationForm


@login_required
def evaluer_directeur(request, agent_id):
    # 1) Autorisation DG
    if not request.user.is_directeur_general():
        return render(request, 'fiches/erreur.html', {'message': "Accès refusé. Vous n'êtes pas DG."})

    # 2) Récupération de l'agent
    agent = get_object_or_404(Agent, id=agent_id)

    # 3) Vérifier la période active
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    if not periode:
        messages.error(request, "⚠️ La période d'évaluation n'est plus ou pas encore active. Contactez le service RH.")
        return redirect('dashboard_dg')

    # 4) Récupérer le semestre
    semestre = int(request.GET.get('semestre', 1))
    if semestre not in [1, 2]:
        semestre = 1

    # 5) Chercher une évaluation existante
    try:
        evaluation = Evaluation.objects.get(
            agent=agent,
            annee=datetime.now().year,
            semestre=semestre
        )
    except Evaluation.DoesNotExist:
        evaluation = None

    # 6) Traitement du formulaire
    if request.method == "POST":
        # Créer une copie mutable des POST data pour forcer les valeurs
        post_data = request.POST.copy()
        post_data['annee'] = datetime.now().year
        post_data['semestre'] = semestre
        post_data['type_personnel'] = 'responsable'

        form = EvaluationForm(post_data, instance=evaluation) if evaluation else EvaluationForm(post_data)

        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.agent = agent
            evaluation.annee = datetime.now().year
            evaluation.semestre = semestre
            evaluation.type_personnel = 'responsable'
            evaluation.save()
            evaluation.calcul_moyennes()

            # Supprimer les anciennes justifications
            JustificationNote.objects.filter(evaluation=evaluation).delete()

            # Liste des critères
            criteres = [
                'connaissances', 'initiative', 'rendement', 'respect_objectifs',
                'civisme', 'service_public', 'relations_humaines', 'discipline',
                'ponctualite', 'assiduite', 'tenue', 'leadership', 'planification',
                'travail_equipe', 'resolution_problemes', 'prise_decision'
            ]

            # Sauvegarder les justifications pour notes 1 ou 5
            for critere in criteres:
                note = request.POST.get(critere)
                justification = request.POST.get(f"{critere}_justif", "").strip()
                if note in ['1', '5'] and justification:
                    JustificationNote.objects.create(
                        evaluation=evaluation,
                        critere=critere,
                        note=int(note),
                        justification=justification
                    )

            # Envoi d'email à l'agent
            user_agent = agent.utilisateur
            if user_agent and user_agent.email:
                subject = "Votre évaluation est disponible"
                message = (
                    f"Bonjour {agent.nom} {agent.prenoms},\n\n"
                    f"Votre évaluation du semestre {semestre} de l'année {evaluation.annee} "
                    f"a été réalisée par votre directeur le {timezone.now().strftime('%d/%m/%Y')}.\n\n"
                    "Vous pouvez la consulter depuis votre espace dédié sur le site (evaluation.stats.ci).\n\n"
                    "Cordialement,\n"
                    "Le service RH"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_agent.email],
                        fail_silently=False,
                    )
                    messages.info(request, "✉️ Un email de notification a été envoyé à l'agent.")
                except Exception as e:
                    messages.warning(request, f"⚠️ Impossible d'envoyer l'email : {e}")

            messages.success(request, f"✅ Évaluation du semestre {semestre} enregistrée avec succès.")
            return redirect('dashboard_dg')
        else:
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs et justifications.")
            # Même en cas d'erreur, transformer les champs en HiddenInput
            from django import forms as django_forms
            form.fields['annee'].widget = django_forms.HiddenInput()
            form.fields['semestre'].widget = django_forms.HiddenInput()
            form.fields['type_personnel'].widget = django_forms.HiddenInput()

    else:
        # GET request : préparer le formulaire
        from django import forms as django_forms

        if evaluation:
            form = EvaluationForm(instance=evaluation)
        else:
            initial_data = {
                'annee': datetime.now().year,
                'semestre': semestre,
                'type_personnel': 'responsable'
            }
            form = EvaluationForm(initial=initial_data)

        # Utiliser des champs cachés au lieu de disabled pour que les valeurs soient envoyées en POST
        form.fields['annee'].widget = django_forms.HiddenInput()
        form.fields['semestre'].widget = django_forms.HiddenInput()
        form.fields['type_personnel'].widget = django_forms.HiddenInput()

    # Définir les listes de critères pour le template
    criteres_rendement = ['connaissances', 'initiative', 'rendement', 'respect_objectifs']
    criteres_comportement = ['civisme', 'service_public', 'relations_humaines', 'discipline',
                             'ponctualite', 'assiduite', 'tenue']
    criteres_management = ['leadership', 'planification', 'travail_equipe',
                           'resolution_problemes', 'prise_decision']

    # Récupérer les justifications existantes
    justifications = {}
    if evaluation:
        for justif in evaluation.justificationnote_set.all():
            justifications[justif.critere] = justif.justification

    return render(request, "fiches/evaluer_directeur_dg.html", {
        "form": form,
        "agent": agent,
        "evaluation": evaluation,
        "semestre": semestre,
        "criteres_rendement": criteres_rendement,
        "criteres_comportement": criteres_comportement,
        "criteres_management": criteres_management,
        "justifications": justifications,
    })



@login_required
def voir_mes_notes_evaluation(request, evaluation_id):
    """
    Affiche uniquement les notes données par l'évaluateur connecté
    - Chef de service : voit rendement + comportement (champs génériques)
    - Sous-directeur : voit rendement + comportement (champs _sous_directeur) + management pour responsables
    """
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    user = request.user

    # Déterminer le rôle de l'utilisateur
    user_role = getattr(user, 'role', None)

    criteres_rendement = []
    criteres_comportement = []
    criteres_management = []

    if user_role == 'chef_service':
        # Chef de service : utilise les champs avec suffixe _chef_service
        criteres_rendement = [
            ('Connaissances et aptitudes professionnelles', evaluation.connaissances_chef_service),
            ('Esprit d\'initiative', evaluation.initiative_chef_service),
            ('Puissance du travail et rendement', evaluation.rendement_chef_service),
            ('Respect des objectifs', evaluation.respect_objectifs_chef_service),
        ]

        criteres_comportement = [
            ('Civisme', evaluation.civisme_chef_service),
            ('Sens du service public', evaluation.service_public_chef_service),
            ('Relations humaines', evaluation.relations_humaines_chef_service),
            ('Esprit de discipline', evaluation.discipline_chef_service),
            ('Ponctualité', evaluation.ponctualite_chef_service),
            ('Assiduité', evaluation.assiduite_chef_service),
            ('Tenue', evaluation.tenue_chef_service),
        ]

    elif user_role == 'sous_directeur':
        # Sous-directeur : utilise les champs avec suffixe _sous_directeur
        criteres_rendement = [
            ('Connaissances et aptitudes professionnelles', evaluation.connaissances_sous_directeur),
            ('Esprit d\'initiative', evaluation.initiative_sous_directeur),
            ('Puissance du travail et rendement', evaluation.rendement_sous_directeur),
            ('Respect des objectifs', evaluation.respect_objectifs_sous_directeur),
        ]

        criteres_comportement = [
            ('Civisme', evaluation.civisme_sous_directeur),
            ('Sens du service public', evaluation.service_public_sous_directeur),
            ('Relations humaines', evaluation.relations_humaines_sous_directeur),
            ('Esprit de discipline', evaluation.discipline_sous_directeur),
            ('Ponctualité', evaluation.ponctualite_sous_directeur),
            ('Assiduité', evaluation.assiduite_sous_directeur),
            ('Tenue', evaluation.tenue_sous_directeur),
        ]

        # Management (pour responsables uniquement)
        if evaluation.type_personnel == 'responsable':
            criteres_management = [
                ('Leadership', evaluation.leadership_sous_directeur),
                ('Planification', evaluation.planification_sous_directeur),
                ('Travail d\'équipe', evaluation.travail_equipe_sous_directeur),
                ('Résolution de problèmes', evaluation.resolution_problemes_sous_directeur),
                ('Prise de décision', evaluation.prise_decision_sous_directeur),
            ]

    # Calculer les moyennes
    moyenne_rendement = None
    moyenne_comportement = None
    moyenne_management = None

    if criteres_rendement:
        notes_rendement = [n for _, n in criteres_rendement if n is not None]
        if notes_rendement:
            moyenne_rendement = round(sum(notes_rendement) / len(notes_rendement), 2)

    if criteres_comportement:
        notes_comportement = [n for _, n in criteres_comportement if n is not None]
        if notes_comportement:
            moyenne_comportement = round(sum(notes_comportement) / len(notes_comportement), 2)

    if criteres_management:
        notes_management = [n for _, n in criteres_management if n is not None]
        if notes_management:
            moyenne_management = round(sum(notes_management) / len(notes_management), 2)

    return render(request, 'fiches/voir_mes_notes.html', {
        'evaluation': evaluation,
        'criteres_rendement': criteres_rendement,
        'criteres_comportement': criteres_comportement,
        'criteres_management': criteres_management,
        'moyenne_rendement': moyenne_rendement,
        'moyenne_comportement': moyenne_comportement,
        'moyenne_management': moyenne_management,
        'user_role': user_role,
    })
