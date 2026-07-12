from django.contrib import admin
from .models import Utilisateur, Livre, Emprunt, DemandeLivre, Commentaire, Like, Notification, EtudiantProxy, AdminProxy
from django import forms
from django.contrib.auth.hashers import make_password
import uuid
from django.contrib.auth.admin import UserAdmin


# CONFIGIRATION

admin.site.site_header = "UniBooks - Administration"
admin.site.site_title = "UniBooks Admin"
admin.site.index_title = "Panneau de gestion"


# FORMULAIRE ETUDIANT

class FormulaireEtudiant(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['matricule', 'first_name', 'last_name', 'email']
        labels = {
            'matricule': 'Matricule *',
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Email',
        }

    def clean_matricule(self):
        matricule = self.cleaned_data.get('matricule', '').strip()
        if not matricule:
            raise forms.ValidationError("Le matricule est obligatoire.")
        if Utilisateur.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return matricule


# FORMULAIRE NOTIFICATION

from django import forms
from .models import Notification

class FormulaireEnvoiNotification(forms.ModelForm):
    envoyer_a_tous = forms.BooleanField(
        required=False,
        label="Envoyer à TOUS les étudiants",
        help_text="Si coché, le champ destinataire est ignoré."
    )

    class Meta:
        model  = Notification
        fields = ['destinataire', 'titre', 'message', 'envoyer_a_tous']
        labels = {
            'destinataire': 'Étudiant destinataire',
            'titre': 'Titre de la notification',
            'message': 'Message',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['destinataire'].required = False

    def clean(self):
        cleaned_data = super().clean()
        envoyer_a_tous = cleaned_data.get('envoyer_a_tous')
        destinataire = cleaned_data.get('destinataire')

        if not envoyer_a_tous and not destinataire:
            raise forms.ValidationError(
                "Erreur : Vous devez soit sélectionner un étudiant, soit cocher 'Envoyer à TOUS les étudiants'."
            )

        return cleaned_data

    
# ADMIN ETUDIANT

@admin.register(EtudiantProxy)
class EtudiantAdmin(admin.ModelAdmin):
    add_form = FormulaireEtudiant

    list_display = ('matricule', 'first_name', 'last_name', 'role', 'is_active', 'doit_changer_mot_de_passe')
    list_filter = ('role', 'is_active')
    search_fields = ('matricule', 'first_name', 'last_name', 'email')
    ordering = ('matricule',)

    fieldsets = (
        ("Informations personnelles", {
            'fields': ('matricule', 'first_name', 'last_name', 'email')
        }),
        ("Accès", {
            'fields': ('is_active', 'doit_changer_mot_de_passe')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=Utilisateur.Role.ETUDIANT)

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.username = str(uuid.uuid4())[:8]
            obj.role = Utilisateur.Role.ETUDIANT
            obj.password = make_password('12345678')
            obj.doit_changer_mot_de_passe = True
        obj.save()
        if not change:
            self.message_user(
                request,
                f"Étudiant '{obj.matricule}' créé. Mot de passe : 12345678",
            )

    actions = ['reinitialiser_mdp']

    @admin.action(description="Forcer le changement de MDP")
    def reinitialiser_mdp(self, request, queryset):
        nb = queryset.update(doit_changer_mot_de_passe=True)
        self.message_user(request, f"{nb} utilisateur(s) devront changer leur MDP.")


# ADMIN ADMIN

@admin.register(AdminProxy)
class AdministrateurAdmin(UserAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            role=Utilisateur.Role.ADMIN
        ) | super().get_queryset(request).filter(is_superuser=True)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.role = Utilisateur.Role.ADMIN
            obj.doit_charger_mot_de_passe = False
        super().save_model(request, obj, form, change)

    fieldsets = UserAdmin.fieldsets + (
        ("Informations BiblioTECH", {
            'fields': ('role', 'matricule', 'doit_changer_mot_de_passe')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations BiblioTECH", {
            'fields': ('first_name', 'last_name', 'email', 'matricule')
        }),
    )


# LIVRE

@admin.register(Livre)
class LivreAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'categorie', 'quantite_totale', 'quantite_disponible', 'date_ajout')
    list_filter = ('categorie',)
    search_fields = ('titre', 'auteur', 'isbn')
    ordering = ('-date_ajout',)
    readonly_fields = ('date_ajout',)

    def quantite_disponible(self, obj):
        return obj.quantite_disponible
    quantite_disponible.short_description = "Disponible"


# EMPRUNT

@admin.register(Emprunt)
class EmpruntAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'livre', 'date_emprunt', 'date_retour_prevue', 'statut')
    list_filter = ('statut',)
    search_fields = ('etudiant__matricule', 'etudiant__first_name', 'livre__titre')
    ordering = ('-date_emprunt',)
    date_hierarchy = 'date_emprunt'


    actions = ['marquer_rendu', 'recalculer_statuts']

    @admin.action(description="Marquer comme Rendus")
    def marquer_rendu(self, request, queryset):
        from django.utils import timezone
        nb = queryset.filter(
            statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD]
        ).update(statut=Emprunt.Statut.RENDU, date_retour_reelle=timezone.now().date())
        self.message_user(request, f"{nb} emprunt(s) marqué(s) comme rendu(s).")

    @admin.action(description="Recalculer les statuts")
    def recalculer_statuts(self, request, queryset):
        nb = 0
        for e in queryset.filter(statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD]):
            e.mettre_a_jour_statut()
            nb += 1
        self.message_user(request, f"{nb} statut(s) recalculé(s).")


# DEMANDE DE LIVRE

@admin.register(DemandeLivre)
class DemandeLivreAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'etudiant', 'statut', 'date_demande')
    list_filter = ('statut',)
    search_fields = ('titre', 'auteur', 'etudiant__matricule')
    ordering = ('-date_demande',)

    actions = ['approuver', 'rejeter']

    @admin.action(description="Approuver")
    def approuver(self, request, queryset):
        nb = queryset.update(statut=DemandeLivre.Statut.APPROUVEE)
        self.message_user(request, f"{nb} demande(s) approuvée(s).")

    @admin.action(description="Rejeter")
    def rejeter(self, request, queryset):
        nb = queryset.update(statut=DemandeLivre.Statut.REJETEE)
        self.message_user(request, f"{nb} demande(s) rejetée(s).")


# COMMENTAIRE

@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'livre', 'parent', 'date_creation')
    search_fields = ('auteur__matricule', 'contenu', 'livre__titre')
    ordering = ('-date_creation',)


# LIKE 

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'commentaire', 'date_like') 


# NOTIFICATION


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    add_form  = FormulaireEnvoiNotification
    form      = FormulaireEnvoiNotification

    list_display  = ('titre', 'destinataire', 'lue', 'date_envoi')
    list_filter   = ('lue',)
    search_fields = ('titre', 'destinataire__matricule', 'destinataire__first_name')
    ordering      = ('-date_envoi',)
    readonly_fields = ('date_envoi',)

    def save_model(self, request, obj, form, change):
        if not change:
            envoyer_a_tous = form.cleaned_data.get('envoyer_a_tous', False)
            
            if envoyer_a_tous:
                etudiants = Utilisateur.objects.filter(
                    role=Utilisateur.Role.ETUDIANT, is_active=True
                )
                
                notifications = [
                    Notification(destinataire=etudiant, titre=obj.titre, message=obj.message)
                    for etudiant in etudiants
                ]
                Notification.objects.bulk_create(notifications)
                
                self.message_user(
                    request,
                    f"Notification envoyée avec succès à {len(notifications)} étudiant(s)."
                )
                
                obj.destinataire = None
                
            else:
                self.message_user(
                    request,
                    f"Notification envoyée à l'étudiant : {obj.destinataire.matricule}."
                )
        
        super().save_model(request, obj, form, change)


