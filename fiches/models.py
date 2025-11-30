'''from django.contrib.auth.models import AbstractUser
from django.db import models

### 📌 Modèle Utilisateur Personnalisé
class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('agent', 'Agent'),
        ('directeur', 'Directeur'),
        ('directeur_general', 'Directeur Général'),
        ('rh', 'RH'),
        ('sous_directeur', 'Sous-directeur'),
        ('chef_service', 'Chef de service'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    matricule = models.CharField(max_length=50, unique=True, null=True, blank=True)

    USERNAME_FIELD = 'username'  # ✅ L'authentification se fait avec le matricule
    REQUIRED_FIELDS = ['email']  # ✅ Seul l'email est obligatoire en plus du matricule

    def is_agent(self):
        return self.role == 'agent'

    def is_directeur(self):
        return self.role == 'directeur'

    def is_directeur_general(self):
        return self.role == 'directeur_general'

    def is_rh(self):
        return self.role == 'rh'

    def is_sous_directeur(self):
        return self.role == 'sous_directeur'

    def is_chef_service(self):
        return self.role == 'chef_service'


    def __str__(self):
        return f"{self.username} ({self.role})"


    def is_directeur(self):
        return hasattr(self, 'direction')

    '''

from django.contrib.auth.models import AbstractUser
from django.db import models

### 📌 Modèle Utilisateur Personnalisé
class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('agent', 'Agent'),
        ('chef_service', 'Chef de service'),
        ('sous_directeur', 'Sous‑directeur'),
        ('directeur', 'Directeur'),
        ('directeur_general', 'Directeur Général'),
        ('rh', 'RH'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='agent',
        help_text="Rôle fonctionnel de l'utilisateur"
    )
    matricule = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Matricule unique (servira de USERNAME_FIELD si souhaité)"
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def is_agent(self):
        """
        Retourne True si l'utilisateur est agent ou appartient
        à un rôle hiérarchiquement supérieur (chef, SD, dir, DG).
        """
        return self.role in (
            'agent',
            'chef_service',
            'sous_directeur',
            'directeur',
            'directeur_general',
        )

    def is_chef_service(self):
        return self.role == 'chef_service'

    def is_sous_directeur(self):
        return self.role == 'sous_directeur'

    def is_directeur(self):
        return self.role == 'directeur'

    def is_directeur_general(self):
        return self.role == 'directeur_general'

    def is_rh(self):
        return self.role == 'rh'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

### 📌 Modèle Direction
class Direction(models.Model):
    nom = models.CharField(max_length=255, unique=True)  # ✅ Nom unique de la direction
    sigle = models.CharField(max_length=20, null=True, blank=True)  # Ex: DIC, DRH, etc.
    directeur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'directeur'},
        related_name="direction",
        null=True, blank=True
    )  # ✅ Chaque direction est dirigée par un unique directeur

    def __str__(self):
        if self.sigle:
            return f"{self.sigle} - {self.nom}"
        return self.nom

class SousDirection(models.Model):
    nom = models.CharField(max_length=255)
    direction = models.ForeignKey(
        Direction,
        on_delete=models.CASCADE,
        related_name='sous_directions'
    )
    #sous_directeur = models.OneToOneField(Utilisateur, null = True, blank = True, related_name = 'sous_direction')
    sous_directeur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'sous_directeur'},
        related_name='sous_direction',
        null=True,     # <— Autorise NULL pour la migration
        blank=True,    # <— Autorise le champ vide dans les forms
    )


class Service(models.Model):
    nom = models.CharField(max_length=255)
    sous_direction = models.ForeignKey(
        SousDirection,
        on_delete=models.CASCADE,
        related_name='services'
    )
    chef_service = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'chef_service'},
        related_name='service'
    )

    class Meta:
        unique_together = ('nom', 'sous_direction')

    def __str__(self):
        return f"{self.nom} – {self.sous_direction.nom}"


### 📌 Modèle Agent
class Agent(models.Model):
    TYPE_PERSONNEL_CHOICES = [
        ('agent', 'Agent'),
        ('responsable', 'Responsable'), ]
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="agent",
        null=True,
        blank=True
    )
    nom = models.CharField(max_length=255)
    prenoms = models.CharField(max_length=255)
    matricule = models.CharField(max_length=50, unique=True)
    date_embauche = models.DateField()
    categorie = models.CharField(max_length=100)

    # ✅ Lien avec la table `Direction` (et non un `Utilisateur`)
    direction = models.ForeignKey(
        Direction, on_delete=models.SET_NULL,
        related_name="agents",
        null=True, blank=True
    )
    sous_direction = models.ForeignKey('SousDirection', on_delete=models.SET_NULL, null=True, blank=True)

    service = models.ForeignKey( Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='agents')
    # ✅ Ajout des champs nécessaires
    poste = models.CharField(max_length=255, blank=True, null=True)
    tenu_depuis = models.DateField(blank=True, null=True)
    # ✅ Champ pour différencier les Agents et les Responsables
    type_personnel = models.CharField(max_length=20, choices=TYPE_PERSONNEL_CHOICES, default='agent')

    def __str__(self):
        return f"{self.nom} {self.prenoms} ({self.matricule})"

from django.db import models
from django.conf import settings

NOTE_CHOICES = [(i, str(i)) for i in range(1, 6)]
SEMESTRE_CHOICES = [
    (1, '1ᵉʳ semestre'),
    (2, '2ᵉ semestre'),
]
TYPE_PERSONNEL = [
    ('agent', 'Agent'),
    ('responsable', 'Responsable'),
]
DECISION_CHOICES = [
    ('formation', 'Formation'),
    ('promotion', 'Promotion'),
    ('augmentation', 'Augmentation de salaire (au mérite)'),
    ('rupture', 'Rupture de contrat'),
    ('autres', 'Autres'),
]

class Evaluation(models.Model):
    # — Liaison & métadonnées —
    agent               = models.ForeignKey('Agent', on_delete=models.CASCADE)
    annee               = models.IntegerField()
    semestre            = models.IntegerField(choices=SEMESTRE_CHOICES)
    type_personnel      = models.CharField(max_length=20, choices=TYPE_PERSONNEL)

    # Qui a saisi la partie management ?
    chef_service_user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'role':'chef_service'},
        related_name='evals_chef_service'
    )
    sous_directeur_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'role':'sous_directeur'},
        related_name='evals_sous_directeur'
    )
    directeur_user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'role':'directeur'},
        related_name='evals_directeur'
    )

    # — M1 : Rendement —
    connaissances_chef_service       = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    connaissances_sous_directeur     = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    connaissances          = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    initiative_chef_service          = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    initiative_sous_directeur        = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    initiative             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    rendement_chef_service           = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    rendement_sous_directeur         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    rendement             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    respect_objectifs_chef_service   = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    respect_objectifs_sous_directeur = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    respect_objectifs      = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    # — M2 : Comportement —
    civisme_chef_service             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    civisme_sous_directeur           = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    civisme                = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    service_public_chef_service      = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    service_public_sous_directeur    = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    service_public         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    relations_humaines_chef_service  = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    relations_humaines_sous_directeur= models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    relations_humaines     = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    discipline_chef_service          = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    discipline_sous_directeur        = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    discipline             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    ponctualite_chef_service         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    ponctualite_sous_directeur       = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    ponctualite            = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    assiduite_chef_service           = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    assiduite_sous_directeur         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    assiduite              = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    tenue_chef_service               = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    tenue_sous_directeur             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    tenue                  = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    # — M3 : Management (pour responsables) —

    leadership_sous_directeur        = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    leadership             = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)


    planification_sous_directeur     = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    planification          = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)


    travail_equipe_sous_directeur    = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    travail_equipe         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)


    resolution_problemes_sous_directeur= models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    resolution_problemes   = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)


    prise_decision_sous_directeur    = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)
    prise_decision         = models.IntegerField(choices=NOTE_CHOICES, null=True, blank=True)

    # — Moyennes calculées (directeur only) —
    moyenne_rendement     = models.FloatField(null=True, blank=True)
    moyenne_comportement  = models.FloatField(null=True, blank=True)
    moyenne_management    = models.FloatField(null=True, blank=True)
    moyenne_generale      = models.FloatField(null=True, blank=True)

    # — Moyennes pondérées annuelles —
    mpa_s1                = models.FloatField(null=True, blank=True)
    mpa_s2                = models.FloatField(null=True, blank=True)
    total_mpa             = models.FloatField(null=True, blank=True)
    moyenne_generale_annuelle = models.FloatField(null=True, blank=True)

    # — Avis libres —
    avis_chef_service     = models.TextField(null=True, blank=True)
    avis_sous_directeur   = models.TextField(null=True, blank=True)
    avis_directeur        = models.TextField(null=True, blank=True)
    avis_agent = models.TextField(null=True, blank=True)

    # — Signatures —
    est_signe_agent       = models.BooleanField(default=False)
    est_signe_directeur   = models.BooleanField(default=False)

    # ✅ Champs de signature DG
    est_signe_dg = models.BooleanField(default=False)
    date_signature_dg = models.DateTimeField(null=True, blank=True)

    # si tu as un modèle Utilisateur custom:
    utilisateur_signature_dg = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='evaluations_signee_dg'
    )

    # seulement si tu gères une image/empreinte de signature:
    signature_dg = models.ImageField(
        upload_to='signatures/', null=True, blank=True
    )

    # — Décision finale & PDF —
    decision_finale       = models.CharField(max_length=50, choices=DECISION_CHOICES, null=True, blank=True)
    autres_decision       = models.TextField(null=True, blank=True)
    fiche_pdf             = models.FileField(
                                upload_to='evaluations/pdfs/%Y/%m/%d/',
                                null=True, blank=True
                            )

    class Meta:
        unique_together = ('agent', 'annee', 'semestre')
        ordering        = ['agent', 'annee', 'semestre']

    def __str__(self):
        return f"{self.agent} · {self.annee} S{self.semestre}"



    def calcul_moyennes(self):
        # Calcul de la moyenne Rendement (M1)
        self.moyenne_rendement = (
                                         self.connaissances +
                                         self.initiative +
                                         self.rendement +
                                         self.respect_objectifs
                                 ) / 4

        # Calcul de la moyenne Comportement (M2)
        self.moyenne_comportement = (
                                            self.civisme +
                                            self.service_public +
                                            self.relations_humaines +
                                            self.discipline +
                                            self.ponctualite +
                                            self.assiduite +
                                            self.tenue
                                    ) / 7

        # Calcul de la moyenne Management (M3) pour les responsables
        if self.type_personnel == 'responsable':
            self.moyenne_management = (
                                              self.leadership +
                                              self.planification +
                                              self.prise_decision +
                                              self.resolution_problemes +
                                              self.travail_equipe
                                      ) / 5
        else:
            self.moyenne_management = 0

        # Calcul de la Moyenne Générale
        if self.type_personnel == 'responsable':
            self.moyenne_generale = (
                                            self.moyenne_rendement * 2 +
                                            self.moyenne_comportement +
                                            self.moyenne_management * 2
                                    ) / 5
        else:
            self.moyenne_generale = (
                                            self.moyenne_rendement * 2 +
                                            self.moyenne_comportement
                                    ) / 3

            # Calcul de la note finale annuelle si semestre == 2
            if self.semestre == 2:
                mpa_s1, mpa_s2, total_mpa, moyenne_generale_annuelle = self.calcul_note_finale_annuelle()
                if mpa_s1 is None:  # Pas de S1, donc pas de moyenne annuelle
                    self.mpa_s1 = None
                    self.mpa_s2 = None
                    self.total_mpa = None
                    self.moyenne_generale_annuelle = None

        # ✅ Sauvegarde des résultats pour tous les profils (agent & responsable)
        self.save()

    def get_moyenne_s1(self):
        """Récupère la moyenne générale du semestre 1 pour le même agent et la même année."""
        try:
            s1_eval = Evaluation.objects.get(
                agent=self.agent,
                annee=self.annee,
                semestre=1
            )
            return s1_eval.moyenne_generale
        except Evaluation.DoesNotExist:
            return None

    def calcul_note_finale_annuelle(self):
        """Calcule la note finale annuelle (S1+S2) si on est au semestre 2."""
        if self.semestre != 2:
            return None, None, None, None  # Pas de calcul si ce n'est pas S2

        moyenne_s1 = self.get_moyenne_s1()
        moyenne_s2 = self.moyenne_generale

        if moyenne_s1 is None:
            return None, None, None, None  # Pas de S1, on ne peut pas calculer

        # Calcul des moyennes pondérées annuelles (MPA)
        mpa_s1 = moyenne_s1 * 1  # Coeff 1 (sur 5)
        mpa_s2 = moyenne_s2 * 2  # Coeff 2 (sur 10)

        # Total des moyennes pondérées
        total_mpa = mpa_s1 + mpa_s2  # Sur 15

        # Moyenne générale annuelle
        moyenne_generale_annuelle = total_mpa / 3  # Sur 5

        # Sauvegarder les valeurs dans l'instance
        self.mpa_s1 = round(mpa_s1, 3)
        self.mpa_s2 = round(mpa_s2, 3)
        self.total_mpa = round(total_mpa, 3)
        self.moyenne_generale_annuelle = round(moyenne_generale_annuelle, 3)

        return self.mpa_s1, self.mpa_s2, self.total_mpa, self.moyenne_generale_annuelle

    @property
    def mp1(self):
        if self.moyenne_rendement is not None:
            return round(self.moyenne_rendement * 2, 3)
        return 0

    @property
    def mp2(self):
        if self.moyenne_comportement is not None:
            return round(self.moyenne_comportement, 3)
        return 0

    @property
    def mp3(self):
        if self.type_personnel == 'responsable' and self.moyenne_management is not None:
            return round(self.moyenne_management * 2, 3)
        return 0

    @property
    def somme_moyennes_ponderees(self):
        total = self.mp1 + self.mp2
        if self.type_personnel == 'responsable':
            total += self.mp3
        return round(total, 3)

    def get_signature_directeur(self):
        # Récupère la signature du directeur associé à l'agent
        directeur = self.agent.direction.directeur
        if directeur and hasattr(directeur, 'userprofile') and directeur.userprofile.signature:
            return directeur.userprofile.signature
        return None

    def __str__(self):
        return f"Évaluation de {self.agent} ({self.agent.matricule}) - {self.annee}/{self.semestre}"

# Profil utilisateur pour stocker la signature des directeurs
class UserProfile(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True)

    def __str__(self):
        return self.user.username


class JustificationNote(models.Model):
    evaluation = models.ForeignKey('Evaluation', on_delete=models.CASCADE, related_name='justifications')
    critere = models.CharField(max_length=100)  # ex: 'discipline'
    note = models.PositiveSmallIntegerField()
    justification = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.critere} : {self.note} (éval {self.evaluation.id})"


class PeriodeEvaluation(models.Model):
    SEMESTRE_CHOICES = [
        (1, '1ᵉʳ semestre'),
        (2, '2ᵉ semestre'),
    ]

    annee      = models.IntegerField()
    semestre   = models.IntegerField(choices=SEMESTRE_CHOICES)
    date_debut = models.DateField()
    date_fin   = models.DateField()
    active     = models.BooleanField(default=False,
                                      help_text="Cochez pour activer cette période")

    class Meta:
        unique_together = ('annee', 'semestre')
        ordering = ['-annee', 'semestre']

    def __str__(self):
        return f"{self.annee} – Sem. {self.semestre} ({'actif' if self.active else 'inactif'})"

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Agent, Evaluation, PeriodeEvaluation, JustificationNote
from .forms import EvaluationForm

def is_sous_directeur(user):
    return user.role == 'sous_directeur'

@login_required
@user_passes_test(is_sous_directeur)
def evaluer_agent_sous_directeur(request, agent_id):
    # 1️⃣ Vérifier qu’une période d’évaluation est active
    periode = PeriodeEvaluation.objects.filter(active=True).first()
    today = timezone.now().date()
    if not periode:
        messages.error(request, "⚠️ Aucune période d’évaluation active. Contactez le service RH.")
        return redirect('dashboard_sous_directeur')
    if today < periode.date_debut or today > periode.date_fin:
        messages.warning(
            request,
            f"🔒 La période d’évaluation va du "
            f"{periode.date_debut.strftime('%d/%m/%Y')} au {periode.date_fin.strftime('%d/%m/%Y')}. "
            "Vous ne pouvez pas évaluer en dehors de cette plage."
        )
        return redirect('dashboard_sous_directeur')

    # 2️⃣ Charger l’agent et vérifier qu’il appartient à la sous-direction
    agent = get_object_or_404(Agent, id=agent_id)
    if agent.sous_direction != request.user.sous_direction:
        messages.error(request, "⚠️ Cet agent n’est pas dans votre sous-direction.")
        return redirect('dashboard_sous_directeur')

    # 3️⃣ Charger l’évaluation existante (le cas échéant)
    evaluation = Evaluation.objects.filter(
        agent=agent,
        annee=periode.annee,
        semestre=periode.semestre
    ).first()

    # 4️处理 Préparer les justifications existantes
    justifications = {
        j.critere: j.justification
        for j in JustificationNote.objects.filter(evaluation=evaluation)
    } if evaluation else {}

    # 5️⃣ Traitement du POST
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.agent = agent
            evaluation.annee = periode.annee
            evaluation.semestre = periode.semestre
            evaluation.type_personnel = agent.type_personnel
            evaluation.save()
            evaluation.calcul_moyennes()

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

            messages.success(request, f"✅ Évaluation du semestre {periode.semestre}/{periode.annee} enregistrée.")
            return redirect('dashboard_sous_directeur')

        else:
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs et justifications.")

    # 6️⃣ GET : afficher le formulaire
    form = EvaluationForm(
        instance=evaluation
    ) if evaluation else EvaluationForm(initial={
        'annee': periode.annee,
        'semestre': periode.semestre,
        'type_personnel': agent.type_personnel
    })

    return render(request, 'fiches/evaluer_agent.html', {
        'form': form,
        'agent': agent,
        'semestre': periode.semestre,
        'justifications': justifications,
    })


# fiches/models.py
from django.db import models
from django.utils import timezone

class EvaluationStats(models.Model):
    evaluation = models.OneToOneField(
        'Evaluation',
        on_delete=models.CASCADE,
        related_name='stats',
        primary_key=True,   # la PK = id de l’évaluation
    )

    # Semestre (pondéré)
    mp1 = models.FloatField(null=True, blank=True)  # /10
    mp2 = models.FloatField(null=True, blank=True)  # /5
    mp3 = models.FloatField(null=True, blank=True)  # /10 si responsable, sinon 0/NULL
    somme_moyennes_ponderees = models.FloatField(null=True, blank=True)  # /15 ou /25

    # Annuelle (si S2)
    mpa_s1 = models.FloatField(null=True, blank=True)       # /5
    mpa_s2 = models.FloatField(null=True, blank=True)       # /10
    total_mpa = models.FloatField(null=True, blank=True)    # /15
    moyenne_generale_annuelle = models.FloatField(null=True, blank=True)  # /5

    # Garder aussi les moyennes simples pour consultation rapide
    moyenne_rendement    = models.FloatField(null=True, blank=True)
    moyenne_comportement = models.FloatField(null=True, blank=True)
    moyenne_management   = models.FloatField(null=True, blank=True)
    moyenne_generale     = models.FloatField(null=True, blank=True)

    # Métadonnées
    computed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Stats #{self.evaluation_id}"
