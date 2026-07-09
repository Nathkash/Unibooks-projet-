from django.shortcuts import redirect

class ForcerChangementMotDePasseMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        urls_exemptees = [
            '/changer-mdp/',
            '/deconnexion/',
            '/connexion/',
        ]

        utilisateur = request.user

        if (
            utilisateur.is_authenticated
            and hasattr(utilisateur, 'doit_changer_mot_de_passe')
            and utilisateur.doit_changer_mot_de_passe
            and not utilisateur.is_staff
            and request.path not in urls_exemptees
            and not request.path.startswith('/static/')
            and not request.path.startswith('/admin/')
        ):
            return redirect('/changer-mdp/')

        return self.get_response(request)