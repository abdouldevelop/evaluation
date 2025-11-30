from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Agent, Evaluation, Utilisateur, Direction, SousDirection, Service

# ✅ Enregistrement du modèle Utilisateur dans Django Admin
@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Rôle', {'fields': ('role',)}),  # ✅ Ajout du champ rôle
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role')}),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)

# ✅ Enregistrement du modèle Direction dans Django Admin
@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'directeur')  # ✅ Affiche le nom de la direction et son directeur
    search_fields = ('nom',)

# ✅ Enregistrement du modèle Agent dans Django Admin
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenoms', 'matricule', 'direction')
    list_filter = ('direction', 'service')
    search_fields = ('nom', 'prenoms', 'matricule')

    # ✅ Afficher uniquement les Directeurs comme choix de "direction"
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "direction":
            kwargs["queryset"] = Direction.objects.all()  # ✅ Liste uniquement les Directions disponibles
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ✅ Enregistrement du modèle Evaluation dans Django Admin
@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('agent', 'annee', 'semestre')
    list_filter = ('annee', 'semestre', 'agent')


@admin.register(SousDirection)
class SousDirectionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'direction', 'sous_directeur')
    list_filter  = ('direction',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sous_direction', 'chef_service')
    list_filter  = ('sous_direction',)
