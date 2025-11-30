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
from .models import Agent, Utilisateur, Direction

class AgentForm(forms.ModelForm):
    """ Formulaire pour ajouter un agent """
    matricule = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Le matricule servira d'identifiant pour l'agent."
    )
    type_personnel = forms.ChoiceField(choices=Agent.TYPE_PERSONNEL_CHOICES, widget=forms.Select(), required=True)

    class Meta:
        model = Agent
        fields = ['nom', 'prenoms', 'matricule', 'date_embauche', 'categorie', 'direction', 'sous_direction', 'service', 'poste', 'tenu_depuis','type_personnel']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenoms': forms.TextInput(attrs={'class': 'form-control'}),
            'date_embauche': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categorie': forms.TextInput(attrs={'class': 'form-control'}),
            'direction': forms.Select(attrs={'class': 'form-control'}),
            'sous_direction': forms.TextInput(attrs={'class': 'form-control'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'poste': forms.TextInput(attrs={'class': 'form-control'}),
            'tenu_depuis': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type_personnel': forms.Select(choices=Agent.TYPE_PERSONNEL_CHOICES)
        }

# fiches/forms.py
from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Evaluation

# fiches/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Evaluation
import re

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            'annee', 'semestre', 'type_personnel',
            'connaissances', 'initiative', 'rendement', 'respect_objectifs',
            'civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualité', 'assiduite', 'tenue',
            'leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision',
            'avis_directeur'
        ]
        widgets = {
            'annee': forms.NumberInput(attrs={'class': 'form-control'}),
            'semestre': forms.Select(choices=[(1, '1er Semestre'), (2, '2ème Semestre')]),
            'type_personnel': forms.Select(choices=[('agent', 'Agent'), ('responsable', 'Responsable')]),
            'connaissances': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'initiative': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'rendement': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'respect_objectifs': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'civisme': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'service_public': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'relations_humaines': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'discipline': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'ponctualité': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'assiduite': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'tenue': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'leadership': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'planification': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'travail_equipe': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'resolution_problemes': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'prise_decision': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'avis_directeur': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get('type_personnel') == 'agent' or (self.instance and self.instance.type_personnel == 'agent'):
            for field in ['leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision']:
                if field in self.fields:
                    self.fields[field].widget.attrs.update({
                        'class': 'note-critere',
                        'id': field,
                        'onchange': 'toggleJustification(this)'
                    })

    def clean(self):
        cleaned_data = super().clean()
        criteres_rendement = ['connaissances', 'initiative', 'rendement', 'respect_objectifs']
        criteres_comportement = ['civisme', 'service_public', 'relations_humaines', 'discipline', 'ponctualité', 'assiduite', 'tenue']
        criteres_management = ['leadership', 'planification', 'travail_equipe', 'resolution_problemes', 'prise_decision']

        criteres = criteres_rendement + criteres_comportement
        if cleaned_data.get('type_personnel') == 'responsable':
            criteres += criteres_management

        for critere in criteres:  # Vérifier uniquement les critères d'évaluation
            note = cleaned_data.get(critere)
            justification = self.data.get(f"{critere}_justif", "").strip()
            if note in [1, 5] and not justification:
                self.add_error(None, f"Une justification est requise pour la note {note} du critère '{critere}'.")

        return cleaned_data

    def clean_avis_directeur(self):
        avis = self.cleaned_data.get('avis_directeur')
        if avis:
            forbidden_chars = r'[@/#&"()§?=*$<>\\]'
            if re.search(forbidden_chars, avis):
                raise ValidationError(
                    "L'avis ne doit pas contenir les caractères suivants : @, /, #, &, \", (, ), §, ?, =, *, $, <, >, \\")
        return avis

class AvisAgentForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['avis_agent']
        widgets = {
            'avis_agent': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Donnez votre avis ici...'}),
        }

    def clean_avis_agent(self):
        avis = self.cleaned_data.get('avis_agent')
        if avis:
            forbidden_chars = r'[@/#&"()§?=*$<>\\]'  # Corrigé ici
            if re.search(forbidden_chars, avis):
                raise ValidationError("L'avis ne doit pas contenir les caractères suivants : @, /, #, &, \", (, ), §, ?, =, *, $, <, >, \\")
        return avis

