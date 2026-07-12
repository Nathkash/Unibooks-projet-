from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError

from .models import Utilisateur, Livre, Emprunt, DemandeLivre, Commentaire, Like, LivreLike, Notification
from .forms  import ConnexionForm, ChangerMotDePasseForm, DemandeForm, CommentaireForm


# AUTHENTIFICATION

def connexion(request):
    if request.user.is_authenticated:
        return redirect('unibooks:dashboard')

    form = ConnexionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        matricule = form.cleaned_data['matricule']
        mot_de_passe = form.cleaned_data['mot_de_passe']

        try:
            u = Utilisateur.objects.get(matricule=matricule)
        except Utilisateur.DoesNotExist:
            messages.error(request, "Matricule ou mot de passe incorrect.")
            return render(request, 'unibooks/connexion.html', {'form': form})

        utilisateur = authenticate(request, username=u.username, password=mot_de_passe)

        if utilisateur is not None:
            login(request, utilisateur)
            if utilisateur.est_admin:
                return redirect('/admin/')
            if utilisateur.doit_changer_mot_de_passe:
                return redirect('unibooks:changer_mdp')
            return redirect('unibooks:dashboard')
        else:
            messages.error(request, "Matricule ou mot de passe incorrect.")

    return render(request, 'unibooks/connexion.html', {'form': form})


def deconnexion(request):
    logout(request)
    return redirect('unibooks:connexion')


@login_required(login_url='unibooks:connexion')
def changer_mot_de_passe(request):
    form = ChangerMotDePasseForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        nouveau_mdp = form.cleaned_data['nouveau_mot_de_passe']
        request.user.set_password(nouveau_mdp)
        request.user.doit_changer_mot_de_passe = False
        request.user.save()

        utilisateur = authenticate(request, username=request.user.username, password=nouveau_mdp)
        if utilisateur:
            login(request, utilisateur)

        messages.success(request, "Mot de passe mis à jour avec succès.")
        return redirect('unibooks:dashboard')

    return render(request, 'unibooks/changer_mdp.html', {'form': form})


# DASHBOARD

@login_required(login_url='unibooks:connexion')
def dashboard(request):
    utilisateur = request.user

    for emprunt in Emprunt.objects.filter(
        etudiant=utilisateur,
        statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD]
    ):
        emprunt.mettre_a_jour_statut()

    nb_emprunts = Emprunt.objects.filter(
        etudiant=utilisateur, 
        statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD]
    ).count()
    nb_retards = Emprunt.objects.filter(
        etudiant=utilisateur, 
        statut=Emprunt.Statut.EN_RETARD
    ).count()
    derniere_demande = DemandeLivre.objects.filter(
        etudiant=utilisateur
    ).first()
    derniers_livres = Livre.objects.order_by(
        '-date_ajout'
    )[:4]
    emprunts_en_retard = Emprunt.objects.filter(
        etudiant=utilisateur, 
        statut=Emprunt.Statut.EN_RETARD
    )

    return render(request, 'unibooks/dashboard.html', {
        'nb_emprunts': nb_emprunts,
        'nb_retards': nb_retards,
        'derniere_demande': derniere_demande,
        'derniers_livres': derniers_livres,
        'emprunts_en_retard': emprunts_en_retard,
    })


# CATALOGUE

@login_required(login_url='unibooks:connexion')
def catalogue(request):
    recherche = request.GET.get('q', '').strip()
    livres = Livre.objects.all()
    if recherche:
        livres = livres.filter(titre__icontains=recherche) | livres.filter(auteur__icontains=recherche)
    return render(request, 'unibooks/catalogue.html', {'livres': livres, 'recherche': recherche})


@login_required(login_url='unibooks:connexion')
def detail_livre(request, pk):
    livre = get_object_or_404(Livre, pk=pk)
    commentaires = Commentaire.objects.filter(
        livre=livre, 
        parent=None
    ).prefetch_related('reponses__auteur', 'likes')
    likes_utilisateur = set(Like.objects.filter(
        utilisateur=request.user, 
        commentaire__livre=livre
    ).values_list('commentaire_id', flat=True))
    form_commentaire  = CommentaireForm()

    return render(request, 'unibooks/detail_livre.html', {
        'livre': livre,
        'commentaires': commentaires,
        'likes_utilisateur': likes_utilisateur,
        'form_commentaire': form_commentaire,
    })


# EMPRUNTS

@login_required(login_url='unibooks:connexion')
def mes_emprunts(request):
    emprunts = Emprunt.objects.filter(
        etudiant=request.user
    ).select_related('livre')
    for e in emprunts:
        e.mettre_a_jour_statut()
    emprunts = Emprunt.objects.filter(
        etudiant=request.user
    ).select_related('livre')
    return render(request, 'unibooks/mes_emprunts.html', {'emprunts': emprunts})


# DEMANDES EMPRUNTS

@login_required(login_url='unibooks:connexion')
def demander_emprunt(request, livre_pk):
    livre = get_object_or_404(Livre, pk=livre_pk)

    if request.method == 'POST':
        existe = DemandeLivre.objects.filter(
            etudiant=request.user,
            titre=livre.titre,
            statut=DemandeLivre.Statut.EN_ATTENTE
        ).exists()

        if existe:
            messages.warning(request, "Vous avez déjà une demande en attente pour ce livre.")
        else:
            DemandeLivre.objects.create(
                etudiant=request.user,
                titre=livre.titre,
                auteur=livre.auteur,
                message=f"Demande d'emprunt pour le livre : {livre.titre}"
            )
            messages.success(request, f"Votre demande d'emprunt pour « {livre.titre} » a été envoyée au bibliothécaire.")

    return redirect('unibooks:detail_livre', pk=livre_pk)


# DEMANDES

@login_required(login_url='unibooks:connexion')
def mes_demandes(request):
    demandes = DemandeLivre.objects.filter(
        etudiant=request.user
    )
    return render(request, 'unibooks/mes_demandes.html', {'demandes': demandes})


@login_required(login_url='unibooks:connexion')
def nouvelle_demande(request):
    form = DemandeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        demande = form.save(commit=False)
        demande.etudiant = request.user
        demande.save()
        messages.success(request, "Votre demande a bien été envoyée.")
        return redirect('unibooks:mes_demandes')
    return render(request, 'unibooks/nouvelle_demande.html', {'form': form})


# COMMENTAIRES

@login_required(login_url='unibooks:connexion')
def ajouter_commentaire(request, livre_pk):
    livre = get_object_or_404(Livre, pk=livre_pk)
    if request.method == 'POST':
        form = CommentaireForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.livre = livre
            commentaire.auteur = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    commentaire.parent = Commentaire.objects.get(
                        pk=parent_id, 
                        livre=livre
                    )
                except Commentaire.DoesNotExist:
                    pass
            commentaire.save()
    return redirect('unibooks:detail_livre', pk=livre_pk)


# LIKES

@login_required(login_url='unibooks:connexion')
def toggler_like(request, commentaire_pk):
    if request.method != 'POST':
        return redirect('unibooks:catalogue')
    commentaire = get_object_or_404(
        Commentaire, 
        pk=commentaire_pk
    )
    try:
        Like.objects.create(
            commentaire=commentaire, 
            utilisateur=request.user
        )
    except IntegrityError:
        Like.objects.filter(
            commentaire=commentaire, 
            utilisateur=request.user
        ).delete()
    return redirect('unibooks:detail_livre', pk=commentaire.livre_id)


@login_required(login_url='unibooks:connexion')
def toggler_like_livre(request, livre_pk):
    if request.method != 'POST':
        return redirect('unibooks:catalogue')
    livre = get_object_or_404(Livre, pk=livre_pk)
    try:
        LivreLike.objects.create(livre=livre, utilisateur=request.user)
    except IntegrityError:
        LivreLike.objects.filter(livre=livre, utilisateur=request.user).delete()
    return redirect('unibooks:detail_livre', pk=livre_pk)


# NOTIFICATIONS

@login_required(login_url='unibooks:connexion')
def notifications(request):
    Notification.objects.filter(
        destinataire=request.user, lue=False
    ).update(lue=True)

    notifs = Notification.objects.filter(destinataire=request.user)
    return render(request, 'unibooks/notifications.html', {'notifs': notifs})


@login_required(login_url='unibooks:connexion')
def marquer_lue(request, pk):
    if request.method == 'POST':
        Notification.objects.filter(
            pk=pk, destinataire=request.user
        ).update(lue=True)
    return redirect('unibooks:notifications')


# PROFIL

@login_required(login_url='unibooks:connexion')
def profil(request):
    return render(request, 'unibooks/profil.html', {'utilisateur': request.user})
