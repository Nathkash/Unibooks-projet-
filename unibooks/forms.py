from django import forms
from .models import DemandeLivre, Commentaire



class ConnexionForm(forms.Form):
    matricule = forms.CharField(
        max_length=50,
        label="Matricule",
        widget=forms.TextInput(attrs={'placeholder': 'Votre matricule', 'autofocus': True})
    )
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )


class ChangerMotDePasseForm(forms.Form):
    nouveau_mot_de_passe = forms.CharField(
        label="Nouveau mot de passe",
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimun 8 caractères'})
    )
    confirmation = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': 'Répétez le mot de passe'})
    )

    def clean(self):
        cleaned_data = super().clean()
        mdp1 = cleaned_data.get('nouveau_mot_de_passe')
        mdp2 = cleaned_data.get('confirmation')
        if mdp1 and mdp2 and mdp1 != mdp2:
            raise forms.ValidationError("Les deux mots de passe ne correspondent pas.")
        return cleaned_data
   

class DemandeForm(forms.ModelForm):
    class Meta:
        model = DemandeLivre
        fields = ['titre', 'auteur', 'message']
        widgets = {
            'titre': forms.TextInput(attrs={'placeholder': 'Titre du livre recherché'}),
            'auteur': forms.Textarea(attrs={'placeholder': 'Auteur (facultatif)'}),
            'message': forms.Textarea(attrs={'placeholder': 'Pourquoi avez-vous besoin de ce livre ?', 'rows': 3}),
        }
        labels = {
            'titre': 'Titre du livre *',
            'auteur': 'Auteur',
            'message': 'Message (facultatif)',
        }


class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ['contenu']
        widgets = {
            'contenu': forms.Textarea(attrs={'placeholder': 'Votre commentaire...', 'rows': 3}),
        }
        labels = {'contenu': ''}