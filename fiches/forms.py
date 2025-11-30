from django import forms
from .models import Agent, Utilisateur


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = '__all__'  # Tous les champs

    # Limite les choix de "direction" aux utilisateurs ayant le rôle "directeur"
    direction = forms.ModelChoiceField(
        queryset=Utilisateur.objects.filter(role='directeur'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'Utilisateur", widget=forms.TextInput(attrs={'class': 'form-control'}))

from django import forms
from .models import Evaluation

class AvisAgentForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['avis_agent']
        widgets = {
            'avis_agent': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Donnez votre avis ici...'}),
        }

from django import forms
from .models import Direction, Utilisateur, Agent

class DirectionForm(forms.ModelForm):
    class Meta:
        model = Direction
        fields = ['nom', 'directeur']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'directeur': forms.Select(attrs={'class': 'form-select'}),
        }

class DirecteurForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['username', 'email', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}, choices=[('directeur', 'Directeur')]),
        }

class ChangerDirectionAgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['direction']
        widgets = {
            'direction': forms.Select(attrs={'class': 'form-select'}),
        }




from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Agent, Utilisateur, Direction, Evaluation

# Choices for notes with blank placeholder
NOTES_CHOICES = [("", "---------")] + [(i, str(i)) for i in range(1, 6)]

class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['nom', 'prenoms', 'matricule', 'date_embauche', 'categorie', 'direction',
                  'sous_direction', 'service', 'poste', 'tenu_depuis', 'type_personnel']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenoms': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'date_embauche': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categorie': forms.TextInput(attrs={'class': 'form-control'}),
            'direction': forms.Select(attrs={'class': 'form-control'}),
            'sous_direction': forms.TextInput(attrs={'class': 'form-control'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'poste': forms.TextInput(attrs={'class': 'form-control'}),
            'tenu_depuis': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type_personnel': forms.Select(choices=Agent.TYPE_PERSONNEL_CHOICES, attrs={'class': 'form-control'}),
        }

'''class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            'annee', 'semestre', 'type_personnel',
            # Rendement
            'connaissances', 'initiative', 'rendement', 'respect_objectifs',
            # Comportement
            'civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualite', 'assiduite', 'tenue',
            # Management
            'leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision',
            # Avis
            'avis_directeur', 'avis_agent'
        ]
        widgets = {
            'annee': forms.NumberInput(attrs={'class': 'form-control'}),
            'semestre': forms.Select(choices=[(1, '1er Semestre'), (2, '2ème Semestre')], attrs={'class': 'form-control'}),
            'type_personnel': forms.Select(choices=[('agent', 'Agent'), ('responsable', 'Responsable')], attrs={'class': 'form-control'}),
            # Rendement
            'connaissances': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'initiative': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'rendement': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'respect_objectifs': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            # Comportement
            'civisme': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'service_public': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'relations_humaines': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'discipline': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'ponctualite': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'assiduite': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'tenue': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            # Management
            'leadership': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'planification': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'travail_equipe': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'resolution_problemes': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'prise_decision': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            # Avis
            'avis_directeur': forms.Textarea(attrs={'rows': 4, 'class': 'form-control','required': True, 'placeholder': 'Votre avis ici...',}),
            'avis_agent': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'required': True, 'placeholder': 'Donnez votre avis ici...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        criteres = [
            'connaissances', 'initiative', 'rendement', 'respect_objectifs',
            'civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualite', 'assiduite', 'tenue'
        ]
        if cleaned_data.get('type_personnel') == 'responsable':
            criteres += ['leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision']


        for crit in criteres:
            note = cleaned_data.get(crit)
            justif = self.data.get(f"{crit}_justif", "").strip()
            if note in [1, 5] and not justif:
                self.add_error(None, f"Une justification est requise pour la note {note} du critère '{crit}'.")
        return cleaned_data

    def clean_avis_directeur(self):
        avis = self.cleaned_data.get('avis_directeur')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis

    def clean_avis_agent(self):
        avis = self.cleaned_data.get('avis_agent')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On s’assure que Django les considère requis
        for name, field in self.fields.items():
            if name not in ('avis_directeur', 'avis_agent'):
                field.required = True
'''

from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Evaluation

NOTES_CHOICES = [(i, str(i)) for i in range(1, 6)]  # si pas déjà défini

class EvaluationForm(forms.ModelForm):
    MGMT_FIELDS = ['leadership', 'planification', 'travail_equipe',
                   'resolution_problemes', 'prise_decision']

    class Meta:
        model = Evaluation
        fields = [
            'annee', 'semestre', 'type_personnel',
            # Rendement
            'connaissances', 'initiative', 'rendement', 'respect_objectifs',
            # Comportement
            'civisme', 'service_public', 'relations_humaines', 'discipline',
            'ponctualite', 'assiduite', 'tenue',
            # Management
            'leadership', 'planification', 'travail_equipe',
            'resolution_problemes', 'prise_decision',
            # Avis
            'avis_directeur', 'avis_agent'
        ]
        '''widgets = {
            'annee': forms.NumberInput(attrs={'class': 'form-control'}),
            'semestre': forms.Select(
                choices=[(1, '1er Semestre'), (2, '2ème Semestre')],
                attrs={'class': 'form-control'}
            ),
            'type_personnel': forms.Select(
                choices=[('agent', 'Agent'), ('responsable', 'Responsable')],
                attrs={'class': 'form-control'}
            ),'''

        widgets = {
            'annee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-custom'
            }),
            'semestre': forms.Select(
                choices=[(1, '1er Semestre'), (2, '2ème Semestre')],
                attrs={
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-custom'
                }
            ),
            'type_personnel': forms.Select(
                choices=[('agent', 'Agent'), ('responsable', 'Responsable'), ('directeur', 'Directeur')],
                attrs={
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-custom'
                }
            ),
            # Rendement
            'connaissances':       forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'initiative':          forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'rendement':           forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'respect_objectifs':   forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            # Comportement
            'civisme':             forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'service_public':      forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'relations_humaines':  forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'discipline':          forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'ponctualite':         forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'assiduite':           forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            'tenue':               forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control'}),
            # Management
            'leadership':          forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere'}),
            'planification':       forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere'}),
            'travail_equipe':      forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere'}),
            'resolution_problemes':forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere'}),
            'prise_decision':      forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere'}),
            # Avis
            'avis_directeur': forms.Textarea(attrs={
                'rows': 4, 'class': 'form-control', 'required': True,
                'placeholder': 'Votre avis ici...',
            }),
            'avis_agent': forms.Textarea(attrs={
                'rows': 3, 'class': 'form-control', 'required': True,
                'placeholder': 'Donnez votre avis ici...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Par défaut, on considère les champs de note "requis"
        for name, field in self.fields.items():
            if name not in ('avis_directeur', 'avis_agent'):
                field.required = True

        # Déterminer le type de personnel le plus fiable :
        # priorité aux données postées, puis instance.agent, puis initial
        t = (self.data.get('type_personnel')
             or getattr(getattr(self.instance, 'agent', None), 'type_personnel', None)
             or self.initial.get('type_personnel'))

        # Si ce n'est PAS un responsable, les 5 champs management ne doivent pas être requis
        if t != 'responsable':
            for f in self.MGMT_FIELDS:
                if f in self.fields:
                    self.fields[f].required = False
                    # enlever l'attribut HTML required si présent
                    self.fields[f].widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super().clean()

        # Déterminer type à nouveau pour la validation
        t = (cleaned_data.get('type_personnel')
             or self.data.get('type_personnel')
             or getattr(getattr(self.instance, 'agent', None), 'type_personnel', None)
             or self.initial.get('type_personnel'))

        # Critères qui s'appliquent
        criteres = [
            'connaissances', 'initiative', 'rendement', 'respect_objectifs',
            'civisme', 'service_public', 'relations_humaines', 'discipline',
            'ponctualite', 'assiduite', 'tenue'
        ]
        if t == 'responsable':
            criteres += self.MGMT_FIELDS

        # Valider la justification SEULEMENT pour les critères concernés
        for crit in criteres:
            note = cleaned_data.get(crit, None)
            # (self.data contient les *_justif si tu les postes avec le form)
            justif = (self.data.get(f"{crit}_justif") or "").strip()
            if note in (1, 5) and not justif:
                self.add_error(None, f"Une justification est requise pour la note {note} du critère « {crit} ».")

        # Si non-responsable, on ignore totalement les champs management dans la validation
        if t != 'responsable':
            for f in self.MGMT_FIELDS:
                # éviter que Django garde une valeur vide qui poserait problème si le modèle n'accepte pas null
                if f in cleaned_data and cleaned_data[f] in ("", None):
                    cleaned_data[f] = None

        return cleaned_data

    def clean_avis_directeur(self):
        avis = self.cleaned_data.get('avis_directeur')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis

    def clean_avis_agent(self):
        avis = self.cleaned_data.get('avis_agent')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis





from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Evaluation

NOTES_CHOICES = [("", "---------")] + [(i, str(i)) for i in range(1, 6)]

class EvaluationFormSousDirecteur(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            'annee', 'semestre', 'type_personnel',
            # Rendement
            'connaissances_sous_directeur', 'initiative_sous_directeur', 'rendement_sous_directeur', 'respect_objectifs_sous_directeur',
            # Comportement
            'civisme_sous_directeur', 'service_public_sous_directeur', 'relations_humaines_sous_directeur',
            'discipline_sous_directeur', 'ponctualite_sous_directeur', 'assiduite_sous_directeur', 'tenue_sous_directeur',
            # Management
            'leadership_sous_directeur', 'planification_sous_directeur', 'travail_equipe_sous_directeur',
            'resolution_problemes_sous_directeur', 'prise_decision_sous_directeur',
            # Avis
            'avis_sous_directeur',
        ]
        widgets = {
            'annee': forms.HiddenInput(),
            'semestre': forms.HiddenInput(),
            'type_personnel': forms.HiddenInput(),
            # Rendement
            'connaissances_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'initiative_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'rendement_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'respect_objectifs_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            # Comportement
            'civisme_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'service_public_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'relations_humaines_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'discipline_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'ponctualite_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'assiduite_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'tenue_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            # Management
            'leadership_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'planification_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'travail_equipe_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'resolution_problemes_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'prise_decision_sous_directeur': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            # Avis
            'avis_sous_directeur': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Donnez votre avis ici...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        criteres = [
            'connaissances_sous_directeur', 'initiative_sous_directeur', 'rendement_sous_directeur', 'respect_objectifs_sous_directeur',
            'civisme_sous_directeur', 'service_public_sous_directeur', 'relations_humaines_sous_directeur',
            'discipline_sous_directeur', 'ponctualite_sous_directeur', 'assiduite_sous_directeur', 'tenue_sous_directeur'
        ]
        if cleaned_data.get('type_personnel') == 'responsable':
            criteres += [
                'leadership_sous_directeur', 'planification_sous_directeur', 'travail_equipe_sous_directeur',
                'resolution_problemes_sous_directeur', 'prise_decision_sous_directeur'
            ]

        for crit in criteres:
            note = cleaned_data.get(crit)
            justif = self.data.get(f"{crit}_justif", "").strip()
            if note in [1, 5] and not justif:
                self.add_error(None, f"Une justification est requise pour la note {note} du critère '{crit.replace('_sous_directeur', '')}'.")
        return cleaned_data

    def clean_avis_sous_directeur(self):
        avis = self.cleaned_data.get('avis_sous_directeur')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis

from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Evaluation
NOTES_CHOICES = [("", "---------")] + [(i, str(i)) for i in range(1, 6)]
class EvaluationFormChefService(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            'annee', 'semestre', 'type_personnel',
            # Rendement
            'connaissances_chef_service', 'initiative_chef_service', 'rendement_chef_service', 'respect_objectifs_chef_service',
            # Comportement
            'civisme_chef_service', 'service_public_chef_service', 'relations_humaines_chef_service',
            'discipline_chef_service', 'ponctualite_chef_service', 'assiduite_chef_service', 'tenue_chef_service',

            # Avis
            'avis_chef_service',
        ]
        widgets = {
            'annee': forms.HiddenInput(),
            'semestre': forms.HiddenInput(),
            'type_personnel': forms.HiddenInput(),
            # Rendement
            'connaissances_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'initiative_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'rendement_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'respect_objectifs_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            # Comportement
            'civisme_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'service_public_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'relations_humaines_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'discipline_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'ponctualite_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'assiduite_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),
            'tenue_chef_service': forms.Select(choices=NOTES_CHOICES, attrs={'class': 'form-control note-critere', 'onchange': 'toggleJustification(this)'}),


            # Avis
            'avis_chef_service': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Donnez votre avis ici...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        criteres = [
            'connaissances_chef_service', 'initiative_chef_service', 'rendement_chef_service', 'respect_objectifs_chef_service',
            'civisme_chef_service', 'service_public_chef_service', 'relations_humaines_chef_service',
            'discipline_chef_service', 'ponctualite_chef_service', 'assiduite_chef_service', 'tenue_chef_service'
        ]
        for crit in criteres:
            note = cleaned_data.get(crit)
            justif = self.data.get(f"{crit}_justif", "").strip()
            if note in [1, 5] and not justif:
                self.add_error(None, f"Une justification est requise pour la note {note} du critère '{crit.replace('_chef_service', '')}'.")
        return cleaned_data

    def clean_avis_chef_service(self):
        avis = self.cleaned_data.get('avis_chef_service')
        if avis and re.search(r'[@/#&"()§?=*$<>\\]', avis):
            raise ValidationError("L'avis ne doit pas contenir de caractères spéciaux invalides.")
        return avis



from django import forms
from .models import PeriodeEvaluation

class PeriodeEvaluationForm(forms.ModelForm):
    class Meta:
        model = PeriodeEvaluation
        fields = ["annee", "semestre", "date_debut", "date_fin", "active"]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin":   forms.DateInput(attrs={"type": "date"}),
        }

