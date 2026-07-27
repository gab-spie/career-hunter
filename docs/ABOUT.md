# À propos

Alternance Hunter automatise une recherche d'alternance ou de stage en finance, de la collecte des offres jusqu'au suivi des candidatures.

## Le pipeline, en une phrase

Il collecte des offres depuis plusieurs sources, les normalise dans un format commun, écarte celles qui ne correspondent pas au bon contrat ou à la bonne rentrée, note les autres sur 10 selon un profil personnalisé, met les meilleures en file, les propose une par une sur Telegram, et tient un Google Sheet à jour en temps réel.

## Les filtres

1. **Type de contrat (strict).** Le flux alternance ne garde que de l'alternance ou de l'apprentissage. Le flux stage ne garde que du stage. Un poste "graduate" ou un CDI est écarté du flux alternance.
2. **Rentrée visée.** On ne garde qu'une campagne précise (par exemple la rentrée de septembre 2027), à partir de la date de début quand elle est connue, ou de l'année lue dans l'intitulé sinon.
3. **Score de pertinence.** Chaque offre reçoit une note sur 10 : mots-clés métier, employeurs cibles, niveau de diplôme, exclusions simples et dures.

Seules les offres qui passent les trois filtres et dépassent un seuil de score sont proposées. Le reste est silencieux, par choix : zéro bruit.

## Les secrets

Aucun identifiant n'est versionné. Le projet attend un dossier `secrets/` local contenant, selon les sources et sorties activées :

```
secrets/
  lba_token.txt                  # jeton de l'API officielle
  telegram_alternance_token.txt  # jeton du bot Telegram
  telegram_chat_id.txt           # identifiant de conversation
  google_service_account.json    # compte de service Google Sheets
```

Ce dossier est exclu du dépôt par `.gitignore`.

## Sources complémentaires

Le projet expose une interface de source simple : un module Python qui fournit une fonction `fetch(profil, config)` renvoyant une liste d'offres normalisées. On active une source en l'ajoutant à `sources_extra` dans la config. Le reste du pipeline (filtres, scoring, livraison, suivi) ne change pas.
