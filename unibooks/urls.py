from django.urls import path
from . import views

app_name = 'unibooks'

urlpatterns = [
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('changer-mdp/', views.changer_mot_de_passe, name='changer_mdp'),
    path('', views.dashboard, name='dashboard'),
    path('catalogue/', views.catalogue, name='catalogue'),
    path('livre/<int:pk>/', views.detail_livre, name='detail_livre'),
    path('livre/<int:livre_pk>/liker/', views.toggler_like_livre, name='liker_livre'),
    path('livre/<int:livre_pk>/commenter/', views.ajouter_commentaire, name='ajouter_commentaire'),
    path('commentaire/<int:commentaire_pk>/liker/', views.toggler_like, name='toggler_like'),
    path('mes-emprunts/', views.mes_emprunts, name='mes_emprunts'),
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('mes-demandes/nouvelle/', views.nouvelle_demande, name='nouvelle_demande'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/lue/', views.marquer_lue, name='marquer_lue'),
    path('profil/', views.profil, name='profil'),
]