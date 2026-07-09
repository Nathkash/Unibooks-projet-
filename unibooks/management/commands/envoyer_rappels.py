from django.core.management.base import BaseCommand
from django.utils import timezone
from unibooks.models import Emprunt

class command(BaseCommand):
    help = (
        "Scanne tous les emprunts en retard, met à jour leurs statuts"
        "et simule l'envoi d'un e-mail de rappel à chaque étudiant concerné."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche les rappels sans modifier la base de données.",
        )
        parser.add_argument(
            '--jours',
            type=int,
            default=0,
            help=(
                "Envoyer un rappel prêventif x jours avant la date de retour."
                "Par défaut 0 (uniquement les emprunts déjà en retard)."
            )
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        jours_avant = options['jours']
        aujourd_hui = timezone.now().date()

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"/nBiblioTECH - Rappels d'emprunt ({aujourd_hui})"
            + (" [MODE DRY-RUN]" if dry_run else "")
        ))
        self.stdout.write("-" * 55)


        # Emprunts déjà en retard

        emprunts_en_retard = Emprunt.objects.filter(
            statut__in=[Emprunt.Statut.EN_COURS, Emprunt.Statut.EN_RETARD],
            date_retour_prevue__lt=aujourd_hui
        ).select_related('etudiant', 'livre')

        nb_retard = 0
        for emprunt in emprunts_en_retard:
            jours_retard = (aujourd_hui - emprunt.date_retour_prevue).days

            if not dry_run and emprunt.statut != Emprunt.Statut.EN_RETARD:
                emprunt.statut = Emprunt.Statut.EN_RETARD
                emprunt.save()

            self._simuler_envoi_mail(
                destinataire=emprunt.etudiant,
                sujet=f"Retard - Retournez << {emprunt.livre.titre} >>",
                corps=(
                    f"Bonjour {emprunt.etudiant.get_full_name() or emprunt.etudiant.username},\n\n"
                    f"Vous avez {jours_retard} jour(s) de retard sur le retour du livre :\n"
                    f"    Titre : {emprunt.livre.titre}\n"
                    f"    Autrur : {emprunt.livre.auteur}\n"
                    f"    Prévu le : {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}\n\n"
                    f"Merci de rapporter ce livre dès que possible à la bibliothèque.\n\n\n"
                    f"- BiblioTECH"
                ),
            )
            nb_retard += 1


        # Emprunts bientôt dus

        nb_preventif = 0
        if jours_avant > 0:
            date_cible = aujourd_hui + timezone.timedelta(days=jours_avant)

            emprunts_bientot = Emprunt.objects.filter(
                statut=Emprunt.Statut.EN_COURS,
                date_retour_prevue=date_cible
            ).select_related('etudiant', 'livre')

            for emprunt in emprunts_bientot:
                self._simuler_envoi_mail(
                    destinataire=emprunt.etudiant,
                    sujet=f"Rappel - << {emprunt.livre.titre} >> à rtourner dans {jours_avant} jour(s)",
                    corps=(
                        f"Bonjour {emprunt.etudiant.get_full_name() or emprunt.etudiant.username},\n\n"
                        f"Ce message est un rappel : vous devez retourner le livre suivant\n"
                        f"dans {jours_retard} jour(s) :\n"
                        f"    Titre : {emprunt.livre.titre}\n"
                        f"    Autrur : {emprunt.livre.auteur}\n"
                        f"    Date limite : {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}\n\n\n"
                        f"- BiblioTECH"                        
                    ),
                )
                nb_preventif += 1


        # Résumé final
        
        self.stdout.write("-" * 55)
        self.stdout.write(
            self.style.SUCCESS(f"Rappels envoyés : {nb_retard} retard(s)")
        )
        if jours_avant > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Rappels préventifs : {nb_preventif} (dans {jours_avant} jour(s))")
            )
        if dry_run:
            self.stdout.write(self.style.WARNING("Aucune donnée modifiée (dry-run)."))
        self.stdout.write("")


# Méthode Utilitaire : simulation d'envoi d'e-mail


def _simuler_envoi_mail(self, destinataire, sujet, corps):
    self.stdout.write(
        self.style.WARNING(f"\nÀ : {destinataire.username}")
    )
    self.stdout.write(f"Sujet : {sujet}")
    self.stdout.write(f"Message : ")
    for ligne in corps.split('\n'):
        self.stdout.write(f"{ligne}")