# 🗓️ Calendrier partagé – Marseille

Calendrier collaboratif des sorties culturelles à Marseille (nov. 2026 → fév. 2027).
100 % Python 3 standard library (`http.server` + `sqlite3`) : aucune dépendance à installer.

## Lancement

```bash
python3 server.py
```

puis ouvrir <http://localhost:8000>

La base `data/app.db` est créée automatiquement au premier lancement, puis seedée avec :

- **10 lieux réels** de Marseille (Espace Julien, La Mürisserie, Théâtre du Carré Rond,
  Strapontin, Café-Théâtre du Tûtard, Théâtre Marie-Jeanne, Casa Consolat, KLAP,
  Friche la Belle de Mai, Couvent Levat) avec adresse et minutes à vélo depuis le Cours Julien ;
- **56 événements** (nov. 2026 → fév. 2027) : DVM des Presque (presque derniers vendredis
  du mois, 20h30, Théâtre Marie-Jeanne), matchs d'impro LIPHO au Tûtard, cabaret d'impro
  Le Bruit Qui Court au Strapontin, programmation de l'Espace Julien et de la Friche…

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
- RSVP « Disponible » / « Intéressé·e » par prénom (prénom conservé en `localStorage`, clic à nouveau pour retirer) ;
- Ajout et suppression d'événements.

## Structure

```
server.py          serveur HTTP + API + seed (stdlib uniquement)
static/index.html  page
static/style.css   styles
static/app.js      logique front (fetch, calendrier, filtres, RSVP)
data/app.db        base SQLite créée automatiquement (non versionnée)
```
