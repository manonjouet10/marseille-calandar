# 🗓️ Calendrier partagé – Marseille

Calendrier collaboratif des sorties culturelles à Marseille (nov. 2026 → fév. 2027).
100 % Python 3 standard library (`http.server` + `sqlite3`) : aucune dépendance à installer.

## Lancement

```bash
python3 server.py
```

puis ouvrir <http://localhost:8000>

Par défaut le serveur écoute en local (`127.0.0.1:8000`). Pour le rendre accessible aux
autres (réseau local, petite machine perso, etc.) :

```bash
HOST=0.0.0.0 PORT=8000 python3 server.py
```

## Dépannage

Rien ne s'affiche sur http://localhost:8000 ?

- Vérifie que le serveur tourne : le terminal doit afficher
  « Calendrier partagé Marseille disponible sur http://localhost:8000 ».
  Sinon, lance `python3 server.py` dans le dossier du projet.
- Si le terminal affiche une erreur de port déjà utilisé, lance plutôt
  `PORT=8001 python3 server.py` puis ouvre <http://localhost:8001>.
- Vérifie que tu es sur la branche `calendrier-marseille` (la branche `main` est vide).
- Depuis un téléphone ou un autre ordinateur du même Wi-Fi : lance
  `HOST=0.0.0.0 python3 server.py` sur la machine qui héberge le serveur, puis ouvre
  `http://<IP-locale-de-cette-machine>:8000` (ex. `http://192.168.1.20:8000`).

La base `data/app.db` est créée automatiquement au premier lancement, puis seedée avec :

- **13 lieux réels** de Marseille, centrés sur le Cours Julien / La Plaine et à moins de
  20 min à vélo (Espace Julien, La Mûrisserie, Le Molotov, Théâtre Marie-Jeanne, Théâtre
  du Carré Rond, Le Non-Lieu, Café-Théâtre du Tûtard, Casa Consolat, Strapontin, Friche la
  Belle de Mai, L'Embobineuse, Couvent Levat, KLAP – Maison pour la danse), avec adresse et
  minutes à vélo depuis le Cours Julien ;
- **60 événements** (nov. 2026 → fév. 2027) : les vrais rendez-vous récurrents — DVM des
  Presque au Théâtre Marie-Jeanne (derniers vendredis du mois : 27 nov., 18 déc. exception,
  29 janv., 26 fév., 20h30), matchs d'impro LIPHO au Tûtard, cabaret d'impro Le Bruit Qui
  Court au Strapontin — plus des dates réelles glanées (Micrographia le 17/11 à la Friche,
  soirée de soutien le 7/11 à l'Embobineuse) et des programmations génériques à remplacer par
  les vraies annonces.

## API REST

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/events` | Liste des événements (avec lieu et RSVP) |
| POST | `/api/events` | Crée un événement `{title, type, venue_id, date, time, description}` |
| GET | `/api/events/{id}` | Détail d'un événement |
| PUT | `/api/events/{id}` | Met à jour un événement (champs partiels acceptés) |
| DELETE | `/api/events/{id}` | Supprime un événement (et ses RSVP) |
| POST | `/api/events/{id}/rsvp` | Pose/met à jour un RSVP `{name, status}` (`available` ou `interested`) |
| DELETE | `/api/events/{id}/rsvp?name=...` | Retire un RSVP |
| GET | `/api/venues` | Lieux (adresse + minutes à vélo depuis le Cours Julien) |
| GET | `/api/types` | Types d'événements disponibles |

## Frontend (`static/`)

- Calendrier du mois (pastilles par jour, clic = défilement vers le jour) + liste détaillée ;
- Filtres : type, lieu, temps max à vélo depuis le Cours Julien ;
- RSVP « ✅ Disponible » / « 🤏 Intéressé·e » par prénom (prénom conservé en `localStorage`, clic à nouveau pour retirer) ;
- Ajout et suppression d'événements.

## Structure

```
server.py          serveur HTTP + API + seed (stdlib uniquement)
static/index.html  page
static/style.css   styles
static/app.js      logique front (fetch, calendrier, filtres, RSVP)
data/app.db        base SQLite créée automatiquement (non versionnée)
```
