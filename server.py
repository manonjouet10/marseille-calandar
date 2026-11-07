#!/usr/bin/env python3
"""Calendrier partagé Marseille — serveur 100 % stdlib (http.server + sqlite3)."""

import json
import os
import re
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

EVENT_TYPES = [
    "concert", "théâtre", "impro", "cabaret", "humour",
    "danse", "exposition", "scène ouverte", "soirée",
]
RSVP_STATUSES = ("available", "interested")

# Lieux réels de Marseille : adresse + minutes à vélo depuis le Cours Julien.
VENUES = [
    ("Espace Julien", "39 cours Julien, 13006 Marseille", 0),
    ("La Mûrisserie", "44 cours Julien, 13006 Marseille", 2),
    ("Le Molotov", "3 place Paul Cézanne, 13006 Marseille", 3),
    ("Théâtre Marie-Jeanne", "56 rue Berlioz, 13006 Marseille", 3),
    ("Théâtre du Carré Rond", "23 rue des Trois Rois, 13006 Marseille", 4),
    ("Le Non-Lieu", "67 rue de la Palud, 13006 Marseille", 7),
    ("Café-Théâtre du Tûtard", "33 rue Ferrari, 13005 Marseille", 7),
    ("Casa Consolat", "1 rue Consolat, 13001 Marseille", 9),
    ("Strapontin", "111 rue de l'Olivier, 13005 Marseille", 10),
    ("Friche la Belle de Mai", "41 rue Jobin, 13003 Marseille", 11),
    ("L'Embobineuse", "11 boulevard Bouès, 13003 Marseille", 12),
    ("Couvent Levat", "52 rue Levat, 13003 Marseille", 12),
    ("KLAP – Maison pour la danse", "5 avenue Rostand, 13003 Marseille", 13),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    bike_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS rsvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'interested')),
    UNIQUE (event_id, name)
);
"""


def build_seed_events():
    events = []

    def add(title, type_, venue, date, time, description):
        events.append((title, type_, venue, date, time, description))

    dvm_title = "DVM – Dernier Vendredi du Mois – Les Presque"
    dvm_desc = ("Rendez-vous d'improvisation des Presque au Théâtre Marie-Jeanne : "
                "chaque DVM est unique, guidé par les suggestions du public. "
                "Exception en décembre : le vendredi 18 déc. au lieu du 25.")
    for d in ("2026-11-27", "2026-12-18", "2027-01-29", "2027-02-26"):
        add(dvm_title, "impro", "Théâtre Marie-Jeanne", d, "20:30", dvm_desc)

    lipho_title = "Match d'impro – LIPHO au Tûtard"
    lipho_desc = ("La Ligue d'Improvisation Phocéenne (LIPHO) dispute ses matchs sur la "
                  "patinoire du Tûtard : thèmes tirés au sort, votes du public, pénalités.")
    for d in ("2026-11-05", "2026-11-12", "2026-11-19", "2026-11-26",
              "2026-12-03", "2026-12-10", "2026-12-17", "2026-12-24", "2026-12-31",
              "2027-01-07", "2027-01-14", "2027-01-21", "2027-01-28",
              "2027-02-04", "2027-02-11", "2027-02-18", "2027-02-25"):
        add(lipho_title, "impro", "Café-Théâtre du Tûtard", d, "20:30", lipho_desc)

    cab_title = "Cabaret d'impro – Le Bruit Qui Court"
    cab_desc = ("Cabaret d'improvisation théâtrale par le collectif Le Bruit Qui Court au "
                "Strapontin. Plein tarif 8 €, réduit 5 €.")
    for d in ("2026-11-13", "2026-11-21", "2026-12-05", "2026-12-19",
              "2027-01-09", "2027-01-23", "2027-02-06", "2027-02-20"):
        add(cab_title, "cabaret", "Strapontin", d, "20:30", cab_desc)

    espace_julien = [
        ("2026-11-04", "20:30", "théâtre", "One-woman-show – « Chambre 212 »", "Humour décalé, 50 places."),
        ("2026-11-14", "21:00", "concert", "Concert rock – plateau marseillais", "Trois groupes locaux sur la grande scène de l'Espace Julien."),
        ("2026-11-25", "20:30", "humour", "Scène ouverte stand-up", "Inscriptions ouvertes aux humoristes amateurs."),
        ("2026-12-09", "21:00", "concert", "Soirée électro – DJ set", "Jusqu'au bout de la nuit au Café Julien."),
        ("2026-12-12", "21:00", "concert", "Concert rap – rap marseillais", "Le rap phocéen à l'honneur."),
        ("2026-12-23", "20:30", "théâtre", "Spectacle de Noël – tout public", "Conte musical pour petits et grands."),
        ("2027-01-13", "21:00", "concert", "Chanson française – soirée acoustique", "Trois artistes en format intimiste."),
        ("2027-01-16", "20:30", "humour", "Stand-up – collectif d'humoristes", "Une soirée de rire avec quatre humoristes invités."),
        ("2027-01-27", "20:30", "théâtre", "Théâtre contemporain – création", "Une compagnie invitée présente sa nouvelle création."),
        ("2027-02-10", "21:00", "concert", "Concert jazz – quartet marseillais", "Jazz acoustique sur la scène de l'Espace Julien."),
        ("2027-02-13", "21:00", "concert", "Concert pop", "Pop urbaine avec électro en première partie."),
        ("2027-02-24", "20:30", "théâtre", "Théâtre – création marseillaise", "Une compagnie locale présente sa dernière création."),
    ]
    for d, t, ty, title, desc in espace_julien:
        add(title, ty, "Espace Julien", d, t, desc)

    friche = [
        ("2026-11-06", "18:00", "exposition", "Vernissage – exposition collective", "Artistes de la Friche et du Couvent Levat."),
        ("2026-11-20", "21:00", "concert", "Concert – musiques du monde", "Trois groupes, trois horizons musicaux."),
        ("2026-12-11", "21:00", "soirée", "Soirée club – DJ set", "Electro et house dans la grande halle."),
        ("2026-12-18", "20:00", "soirée", "Noël à la Friche – marché & concert", "Marché de créateurs puis concert en soirée."),
        ("2027-01-15", "18:00", "exposition", "Exposition photo – « Marseille en hiver »", "Photos de quartier par des photographes locaux."),
        ("2027-01-29", "21:00", "concert", "Concert rock – scène de la Friche", "Rock et post-punk à l'affiche."),
        ("2027-02-12", "19:00", "soirée", "Apéro-concert", "Apéro dès 19h, concert à 20h30."),
        ("2027-02-26", "20:00", "soirée", "Grande soirée de clôture de saison", "Concerts, performances et surprises."),
    ]
    for d, t, ty, title, desc in friche:
        add(title, ty, "Friche la Belle de Mai", d, t, desc)

    add("Théâtre – « Qui est Monsieur Schmitt ? »", "théâtre", "Théâtre du Carré Rond",
        "2026-11-11", "20:30", "La compagnie du Carré Rond revisite Sébastien Thiery. 49 places.")
    add("Concert chanson – voix & guitare", "concert", "Théâtre du Carré Rond",
        "2027-01-20", "20:30", "Soirée chanson française au Carré Rond.")
    add("Concert folk – duo marseillais", "concert", "La Mûrisserie",
        "2026-12-12", "21:00", "Concert intimiste au bistrot de la Mûrisserie.")
    add("Scène ouverte – poésie & musique", "scène ouverte", "La Mûrisserie",
        "2027-02-27", "21:00", "Scène ouverte : 10 minutes par artiste, inscription sur place.")
    add("Concert jazz – cantine de la Casa", "concert", "Casa Consolat",
        "2026-11-18", "19:00", "Jazz à la cantine associative de la Casa Consolat, repas possible sur place.")
    add("Danse contemporaine – Kelemenis & cie", "danse", "KLAP – Maison pour la danse",
        "2027-01-30", "20:30", "La compagnie Kelemenis & cie présente sa nouvelle création au KLAP.")
    add("Vernissage – expo des résident·es du Couvent", "exposition", "Couvent Levat",
        "2026-12-16", "18:00", "Découvrez les ateliers des résident·es du Couvent Levat, Belle de Mai.")

    add("Micrographia – concert", "concert", "Friche la Belle de Mai",
        "2026-11-17", "19:00", "Concert à la Friche la Belle de Mai, à partir de 6 €.")
    add("Soirée de soutien à la salle Gueule – Orsini, La Casa Fantom, Monastr, Leonard Kotik",
        "concert", "L'Embobineuse",
        "2026-11-07", "21:00", "Post-punk, noise et doom crust. 7 € + 2 € adhésion.")
    add("Concert rock – plateau marseillais", "concert", "Le Molotov",
        "2026-11-14", "21:00", "Petite salle de la Plaine, programmation alternative (ex-Balthazar).")
    add("Chanson – scène ouverte", "scène ouverte", "Le Non-Lieu",
        "2026-11-26", "20:30", "Scène ouverte chanson au Non-Lieu, rue de la Palud.")

    return events


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def seed(conn):
    if conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]:
        return
    conn.executemany(
        "INSERT INTO venues (name, address, bike_minutes) VALUES (?, ?, ?)", VENUES
    )
    venue_ids = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM venues")}
    rows = [
        (title, type_, venue_ids[venue], date, time, description)
        for title, type_, venue, date, time, description in build_seed_events()
    ]
    conn.executemany(
        "INSERT INTO events (title, type, venue_id, date, time, description) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def valid_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def valid_time(value):
    if not isinstance(value, str) or not TIME_RE.match(value):
        return False
    hours, minutes = value.split(":")
    return int(hours) < 24 and int(minutes) < 60


def validate_event_payload(data, conn, partial=False):
    fields = {}
    if not partial or "title" in data:
        title = str(data.get("title") or "").strip()
        if not title:
            return None, "Le champ 'title' est requis."
        fields["title"] = title[:200]
    if not partial or "type" in data:
        type_ = str(data.get("type") or "").strip()
        if type_ not in EVENT_TYPES:
            return None, "Le champ 'type' doit être l'un de : " + ", ".join(EVENT_TYPES)
        fields["type"] = type_
    if not partial or "venue_id" in data:
        try:
            venue_id = int(data.get("venue_id"))
        except (TypeError, ValueError):
            return None, "Le champ 'venue_id' doit être un entier."
        if not conn.execute("SELECT 1 FROM venues WHERE id = ?", (venue_id,)).fetchone():
            return None, "Lieu inconnu (venue_id)."
        fields["venue_id"] = venue_id
    if not partial or "date" in data:
        if not valid_date(data.get("date")):
            return None, "Le champ 'date' doit être au format YYYY-MM-DD."
        fields["date"] = data["date"]
    if not partial or "time" in data:
        if not valid_time(data.get("time")):
            return None, "Le champ 'time' doit être au format HH:MM."
        fields["time"] = data["time"]
    if "description" in data or not partial:
        fields["description"] = str(data.get("description") or "")[:2000]
    if partial and not fields:
        return None, "Aucun champ à mettre à jour."
    return fields, None


class Handler(BaseHTTPRequestHandler):
    server_version = "CalendrierPartageMarseille/1.0"

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message):
        self._json({"error": message}, status)

    def _empty(self, status=204):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _event_row(self, conn, event_id):
        row = conn.execute(
            """
            SELECT e.id, e.title, e.type, e.date, e.time, e.description, e.venue_id,
                   v.name AS venue_name, v.address AS venue_address,
                   v.bike_minutes AS venue_bike_minutes
            FROM events e JOIN venues v ON v.id = e.venue_id
            WHERE e.id = ?
            """,
            (event_id,),
        ).fetchone()
        if not row:
            return None
        event = dict(row)
        rsvps = [
            {"name": r["name"], "status": r["status"]}
            for r in conn.execute(
                "SELECT name, status FROM rsvps WHERE event_id = ? ORDER BY name", (event_id,)
            )
        ]
        event["rsvps"] = rsvps
        event["n_available"] = sum(1 for r in rsvps if r["status"] == "available")
        event["n_interested"] = sum(1 for r in rsvps if r["status"] == "interested")
        return event

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/venues":
            conn = get_db()
            venues = [dict(r) for r in conn.execute("SELECT * FROM venues ORDER BY bike_minutes")]
            conn.close()
            return self._json({"venues": venues})
        if path == "/api/types":
            return self._json({"types": EVENT_TYPES})
        if path == "/api/events":
            conn = get_db()
            rows = conn.execute(
                """
                SELECT e.id, e.title, e.type, e.date, e.time, e.description, e.venue_id,
                       v.name AS venue_name, v.address AS venue_address,
                       v.bike_minutes AS venue_bike_minutes
                FROM events e JOIN venues v ON v.id = e.venue_id
                ORDER BY e.date, e.time, e.id
                """
            ).fetchall()
            rsvps = conn.execute("SELECT event_id, name, status FROM rsvps").fetchall()
            conn.close()
            by_event = {}
            for r in rsvps:
                by_event.setdefault(r["event_id"], []).append({"name": r["name"], "status": r["status"]})
            events = []
            for row in rows:
                event = dict(row)
                rl = by_event.get(event["id"], [])
                event["rsvps"] = rl
                event["n_available"] = sum(1 for x in rl if x["status"] == "available")
                event["n_interested"] = sum(1 for x in rl if x["status"] == "interested")
                events.append(event)
            return self._json({"events": events})
        m = re.fullmatch(r"/api/events/(\d+)", path)
        if m:
            conn = get_db()
            event = self._event_row(conn, int(m.group(1)))
            conn.close()
            if not event:
                return self._error(404, "Événement introuvable.")
            return self._json(event)
        return self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/events":
            data = self._read_json()
            if data is None:
                return self._error(400, "JSON invalide.")
            conn = get_db()
            fields, err = validate_event_payload(data, conn)
            if err:
                conn.close()
                return self._error(400, err)
            cur = conn.execute(
                "INSERT INTO events (title, type, venue_id, date, time, description) VALUES (?, ?, ?, ?, ?, ?)",
                (fields["title"], fields["type"], fields["venue_id"], fields["date"], fields["time"], fields["description"]),
            )
            conn.commit()
            event = self._event_row(conn, cur.lastrowid)
            conn.close()
            return self._json(event, 201)
        m = re.fullmatch(r"/api/events/(\d+)/rsvp", path)
        if m:
            event_id = int(m.group(1))
            data = self._read_json()
            if data is None:
                return self._error(400, "JSON invalide.")
            name = str(data.get("name") or "").strip()
            status = data.get("status")
            if not name:
                return self._error(400, "Le champ 'name' est requis.")
            if status not in RSVP_STATUSES:
                return self._error(400, "Le champ 'status' doit être 'available' ou 'interested'.")
            conn = get_db()
            if not conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone():
                conn.close()
                return self._error(404, "Événement introuvable.")
            conn.execute(
                """
                INSERT INTO rsvps (event_id, name, status) VALUES (?, ?, ?)
                ON CONFLICT (event_id, name) DO UPDATE SET status = excluded.status
                """,
                (event_id, name, status),
            )
            conn.commit()
            conn.close()
            return self._json({"event_id": event_id, "name": name, "status": status}, 201)
        return self._error(404, "Not found")

    def do_PUT(self):
        path = urlparse(self.path).path
        m = re.fullmatch(r"/api/events/(\d+)", path)
        if not m:
            return self._error(404, "Not found")
        event_id = int(m.group(1))
        data = self._read_json()
        if data is None:
            return self._error(400, "JSON invalide.")
        conn = get_db()
        if not conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone():
            conn.close()
            return self._error(404, "Événement introuvable.")
        fields, err = validate_event_payload(data, conn, partial=True)
        if err:
            conn.close()
            return self._error(400, err)
        assignments = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE events SET {assignments} WHERE id = ?", (*fields.values(), event_id))
        conn.commit()
        event = self._event_row(conn, event_id)
        conn.close()
        return self._json(event)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        m = re.fullmatch(r"/api/events/(\d+)/rsvp", path)
        if m:
            event_id = int(m.group(1))
            name = (parse_qs(parsed.query).get("name") or [None])[0]
            if name is None:
                data = self._read_json()
                if data is None:
                    return self._error(400, "JSON invalide.")
                name = str(data.get("name") or "").strip()
            if not name:
                return self._error(400, "Le champ 'name' est requis.")
            conn = get_db()
            cur = conn.execute(
                "DELETE FROM rsvps WHERE event_id = ? AND name = ?", (event_id, name)
            )
            conn.commit()
            conn.close()
            if cur.rowcount == 0:
                return self._error(404, "RSVP introuvable.")
            return self._empty(204)
        m = re.fullmatch(r"/api/events/(\d+)", path)
        if m:
            event_id = int(m.group(1))
            conn = get_db()
            cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()
            if cur.rowcount == 0:
                return self._error(404, "Événement introuvable.")
            return self._empty(204)
        return self._error(404, "Not found")

    def _serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not full.startswith(STATIC_DIR + os.sep) or not os.path.isfile(full):
            return self._error(404, "Not found")
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db()
    init_db(conn)
    seed(conn)
    conn.close()
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print(f"Impossible d'écouter sur {HOST}:{PORT} ({exc}).")
        print("Port déjà utilisé ? Essaie par exemple : PORT=8001 python3 server.py")
        raise SystemExit(1)
    host_label = "localhost" if HOST in ("127.0.0.1", "0.0.0.0", "::1") else HOST
    print(f"Calendrier partagé Marseille disponible sur http://{host_label}:{PORT}")
    if HOST == "0.0.0.0":
        print(f"Depuis un autre appareil du même réseau : http://<IP-de-cette-machine>:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
