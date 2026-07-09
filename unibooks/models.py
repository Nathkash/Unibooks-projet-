from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# UTILISATEUR PERSONALISÉ

class Utilisateur(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administratuer (Biblio)'
        ETUDIANT = 'ETUDIANT', 'Étudiant'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.ETUDIANT,
        verbose_name="Rôle"
    )
    matricule = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Matricule"
    )
    email = models.EmailField(
        blank=True, 
        null=True, 
        verbose_name="Email"
    )
    doit_changer_mot_de_passe = models.BooleanField(
        default=True,
        verbose_name="Doit changer son mot de passe",
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        if self.is_superuser and self.role == self.Role.ETUDIANT:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
    
    @property
    def est_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
    
    @property
    def est_etudiant(self):
        return self.role == self.Role.ETUDIANT
    

# LIVRE

class Livre(models.Model):
    titre = models.CharField(
        max_length=255, 
        verbose_name="Titre"
    )
    auteur = models.CharField(
        max_length=255, 
        verbose_name="Auteur"
    )
    isbn = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ISBN"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Description"
    )
    categorie = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Catégorie"
    )
    quantite_totale = models.PositiveIntegerField(
        default=1, 
        verbose_name="Quantité totale"
    )
    date_ajout = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Date d'ajout"
    )
    image = models.ImageField(
        upload_to='livres/',
        blank=True, null=True,
        verbose_name="Image de couverture"
    )
    image_url = models.URLField(
        blank=True, null=True,
        verbose_name="URL de couverture"
    )

    class Meta:
        verbose_name = "Livre"
        verbose_name_plural = "Livres"
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.titre} - {self.auteur}"
    
    @property
    def quantite_disponible(self):
        empruntes = self.emprunts.filter(
            statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD]
        ).count()
        return max(0, self.quantite_totale - empruntes)
    
    @property
    def est_disponible(self):
        return self.quantite_disponible > 0
    
    @property
    def photo(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return None
    

# EMPRUNT

class Emprunt(models.Model):
    class Statut(models.TextChoices):
        EN_COURS = 'EN_COURS', 'En cours'
        RENDU = "RENDU", 'Rendu'
        EN_RETARD = "EN_RETARD", 'En retard'

    etudiant = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name='emprunts',
        limit_choices_to={'role': Utilisateur.Role.ETUDIANT},
        verbose_name="Étudiant"
    )
    livre = models.ForeignKey(
        Livre,
        on_delete=models.PROTECT,
        related_name='emprunts',
        verbose_name="Livre"
    )
    date_emprunt = models.DateField(
        default=timezone.now, 
        verbose_name="Date d'emprunt"
    )
    date_retour_prevue = models.DateField(
        verbose_name="Date de retour prévue"
    )
    date_retour_reelle = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de retour réelle"
    )
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.EN_COURS,
        verbose_name="Statut"
    )

    class Meta:
        verbose_name = "Emprunt"
        verbose_name_plural = "Emprunts"
        ordering = ['-date_emprunt']

    def __str__(self):
        return f"{self.etudiant} → {self.livre.titre}"
    
    def mettre_a_jour_statut(self):
        if self.statut == self.Statut.RENDU:
            return
        if timezone.now().date() > self.date_retour_prevue:
            self.statut = self.Statut.EN_RETARD
        else:
            self.statut = self.Statut.EN_COURS
        self.save()

    @property
    def est_en_retard(self):
        if self.statut == self.Statut.RENDU:
            return False
        return timezone.now().date() > self.date_retour_prevue
    

# DEMANDE DE LIVRE

class DemandeLivre(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        APPROUVEE = 'APPROUVEE', 'Approuvée'
        REJETEE = 'REJETEE', 'Rejetée'

    etudiant = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='demandes',
        verbose_name="Étudiant"
    )
    titre = models.CharField(
        max_length=255, 
        verbose_name="Titre du livre"
    )
    auteur = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Auteur"
    )
    message = models.TextField(
        blank=True,
        verbose_name="Message",
    )
    statut = models.CharField(
        max_length=12,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name="Statut"
    )
    date_demande = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Date de la demande"
    )

    class Meta:
        verbose_name = "Demande de livre"
        verbose_name_plural = "Demandes de livres"
        ordering = ['-date_demande']

    def __str__(self):
        return f'"{self.titre}" demandé par {self.etudiant}'


# COMMENTAIRE

class Commentaire(models.Model):
    livre = models.ForeignKey(
        Livre,
        on_delete=models.CASCADE,
        related_name='commentaire',
        verbose_name="Livre"
    )
    auteur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Auteur"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='reponses',
        blank=True,
        null=True,
        verbose_name="Réponse à"
    )
    contenu = models.TextField(verbose_name="Contenu")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['date_creation']

    def __str__(self):
        prefix = f"↳ Réponse à #{self.parent_id} - "if self.parent else ""
        return f"{self.auteur} sur '{self.livre.titre}"
    

# LIKE

class Like(models.Model):
    commentaire = models.ForeignKey(
        Commentaire,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="Commentaire"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="Utilisateur"
    )
    date_like = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        unique_together = ('commentaire', 'utilisateur')

    def __str__(self):
        return f"{self.utilisateur} ❤︎ commentaire #{self.commentaire_id}"
    

class EtudiantProxy(Utilisateur):
    class Meta:
        proxy = True
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"

class AdminProxy(Utilisateur):
    class Meta:
        proxy = True
        verbose_name = "Administrateur"
        verbose_name_plural = "Administrateurs"