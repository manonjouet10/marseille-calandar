const LS_KEY = "calendrier-marseille-prenom";
const MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
  "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
const DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];
const TYPE_LABELS = {
  concert: "Concert", théâtre: "Théâtre", impro: "Impro",
  cabaret: "Cabaret", humour: "Humour", danse: "Danse",
  exposition: "Expo", "scène ouverte": "Scène ouverte", soirée: "Soirée",
};

const state = {
  events: [],
  venues: [],
  types: [],
  month: monthStr(new Date()),
  filters: { type: "", venueId: "", maxBike: 20 },
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function monthStr(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(offset) {
  const [y, m] = state.month.split("-").map(Number);
  const d = new Date(y, m - 1 + offset, 1);
  state.month = monthStr(d);
  render();
}

function getPrenom() {
  return (localStorage.getItem(LS_KEY) || "").trim();
}

async function api(path, options = {}) {
  if (options.body) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(path, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.error) || `Erreur HTTP ${res.status}`);
  return data;
}

async function loadAll() {
  const [venuesData, eventsData, typesData] = await Promise.all([
    api("/api/venues"), api("/api/events"), api("/api/types"),
  ]);
  state.venues = venuesData.venues;
  state.events = eventsData.events;
  state.types = typesData.types;
  renderFilters();
  render();
}

function filteredEvents() {
  const f = state.filters;
  return state.events
    .filter(e => e.date.startsWith(state.month))
    .filter(e => !f.type || e.type === f.type)
    .filter(e => !f.venueId || String(e.venue_id) === f.venueId)
    .filter(e => e.venue_bike_minutes <= f.maxBike)
    .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time));
}

function renderFilters() {
  const typeSel = document.getElementById("filter-type");
  typeSel.innerHTML = '<option value="">Tous les types</option>' + state.types
    .map(t => `<option value="${esc(t)}">${esc(TYPE_LABELS[t] || t)}</option>`).join("");
  typeSel.value = state.filters.type;

  const venueSel = document.getElementById("filter-venue");
  venueSel.innerHTML = '<option value="">Tous les lieux</option>' + state.venues
    .map(v => `<option value="${v.id}">${esc(v.name)} (🚲 ${v.bike_minutes} min)</option>`).join("");
  venueSel.value = state.filters.venueId;

  const fType = document.getElementById("f-type");
  fType.innerHTML = state.types
    .map(t => `<option value="${esc(t)}">${esc(TYPE_LABELS[t] || t)}</option>`).join("");
  const fVenue = document.getElementById("f-venue");
  fVenue.innerHTML = state.venues
    .map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join("");
}

function render() {
  renderCalendar();
  renderList();
  const label = document.getElementById("month-label");
  const [y, m] = state.month.split("-").map(Number);
  label.textContent = `${MONTHS_FR[m - 1]} ${y}`;
  document.getElementById("list-title").textContent =
    `Événements de ${MONTHS_FR[m - 1]} ${y} (filtrés)`;
}

function renderCalendar() {
  const cal = document.getElementById("calendar");
  const [y, m] = state.month.split("-").map(Number);
  const first = new Date(y, m - 1, 1);
  const daysInMonth = new Date(y, m, 0).getDate();
  const offset = (first.getDay() + 6) % 7;
  const today = monthStr(new Date()) === state.month ? new Date().getDate() : -1;
  const events = filteredEvents();
  const byDay = {};
  for (const e of events) (byDay[e.date] = byDay[e.date] || []).push(e);

  let html = "";
  for (let i = 0; i < offset; i++) html += '<div class="day empty"></div>';
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${state.month}-${String(d).padStart(2, "0")}`;
    const dayEvents = byDay[date] || [];
    html += `<div class="day${d === today ? " today" : ""}" data-date="${date}" title="${dayEvents.length} événement(s)">
      <span class="num">${d}</span>
      <span class="dots">${dayEvents.map(() => '<span class="dot"></span>').join("")}</span>
    </div>`;
  }
  cal.innerHTML = html;
  cal.querySelectorAll(".day[data-date]").forEach(el => {
    el.addEventListener("click", () => {
      const target = document.getElementById("day-" + el.dataset.date);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function rsvpNames(rsvps, status) {
  return rsvps.filter(r => r.status === status).map(r => r.name);
}

function renderList() {
  const list = document.getElementById("event-list");
  const events = filteredEvents();
  if (!events.length) {
    list.innerHTML = '<p class="empty-msg">Aucun événement ce mois-ci avec ces filtres.</p>';
    return;
  }
  const prenom = getPrenom();
  const byDay = {};
  for (const e of events) (byDay[e.date] = byDay[e.date] || []).push(e);

  let html = "";
  for (const date of Object.keys(byDay).sort()) {
    const [y, m, d] = date.split("-").map(Number);
    const weekday = DAYS_FR[new Date(y, m - 1, d).getDay() === 0 ? 6 : new Date(y, m - 1, d).getDay() - 1];
    html += `<div class="day-group" id="day-${date}"><h3>${weekday} ${d} ${MONTHS_FR[m - 1]}</h3>`;
    for (const e of byDay[date]) {
      const avail = rsvpNames(e.rsvps, "available");
      const inter = rsvpNames(e.rsvps, "interested");
      const mineAvail = prenom && avail.includes(prenom);
      const mineInter = prenom && inter.includes(prenom);
      html += `
      <article class="event-card">
        <div class="head">
          <h4>${esc(e.title)}</h4>
          <button class="delete-event" data-delete="${e.id}" title="Supprimer l'événement">🗑 supprimer</button>
        </div>
        <div class="meta">
          <span class="badge">${esc(TYPE_LABELS[e.type] || e.type)}</span>
          ${esc(e.time)} · <strong>${esc(e.venue_name)}</strong> ·
          <span title="${esc(e.venue_address)}">${esc(e.venue_address)}</span>
          · <span class="bike">🚲 ${e.venue_bike_minutes} min</span>
        </div>
        ${e.description ? `<p class="desc">${esc(e.description)}</p>` : ""}
        <div class="rsvps">
          <span class="count">✅ ${e.n_available} disponible${e.n_available > 1 ? "s" : ""}${avail.length ? " : " + esc(avail.join(", ")) : ""}</span>
          <span class="count">🙋 ${e.n_interested} intéressé·e${e.n_interested > 1 ? "s" : ""}${inter.length ? " : " + esc(inter.join(", ")) : ""}</span>
          <button class="available${mineAvail ? " mine" : ""}" data-rsvp="available" data-id="${e.id}">Disponible</button>
          <button class="interested${mineInter ? " mine" : ""}" data-rsvp="interested" data-id="${e.id}">Intéressé·e</button>
        </div>
      </article>`;
    }
    html += "</div>";
  }
  list.innerHTML = html;

  list.querySelectorAll("button[data-rsvp]").forEach(btn => {
    btn.addEventListener("click", () => onRsvp(Number(btn.dataset.id), btn.dataset.rsvp));
  });
  list.querySelectorAll("button[data-delete]").forEach(btn => {
    btn.addEventListener("click", () => onDelete(Number(btn.dataset.delete)));
  });
}

async function onRsvp(eventId, status) {
  const prenom = getPrenom();
  if (!prenom) {
    alert("Entre d'abord ton prénom en haut de page pour poser un RSVP.");
    document.getElementById("prenom").focus();
    return;
  }
  const event = state.events.find(e => e.id === eventId);
  const mine = event && event.rsvps.find(r => r.name === prenom);
  try {
    if (mine && mine.status === status) {
      await api(`/api/events/${eventId}/rsvp?name=${encodeURIComponent(prenom)}`, { method: "DELETE" });
    } else {
      await api(`/api/events/${eventId}/rsvp`, { method: "POST", body: { name: prenom, status } });
    }
    await reloadEvents();
  } catch (err) {
    alert(err.message);
  }
}

async function onDelete(eventId) {
  const event = state.events.find(e => e.id === eventId);
  if (!event || !confirm(`Supprimer « ${event.title} » ?`)) return;
  try {
    await api(`/api/events/${eventId}`, { method: "DELETE" });
    await reloadEvents();
  } catch (err) {
    alert(err.message);
  }
}

async function reloadEvents() {
  const data = await api("/api/events");
  state.events = data.events;
  render();
}

function bind() {
  const prenomInput = document.getElementById("prenom");
  prenomInput.value = localStorage.getItem(LS_KEY) || "";
  prenomInput.addEventListener("input", () => {
    localStorage.setItem(LS_KEY, prenomInput.value);
    renderList();
  });

  document.getElementById("prev-month").addEventListener("click", () => shiftMonth(-1));
  document.getElementById("next-month").addEventListener("click", () => shiftMonth(1));

  document.getElementById("filter-type").addEventListener("change", e => {
    state.filters.type = e.target.value; render();
  });
  document.getElementById("filter-venue").addEventListener("change", e => {
    state.filters.venueId = e.target.value; render();
  });
  const bike = document.getElementById("filter-bike");
  bike.addEventListener("input", () => {
    state.filters.maxBike = Number(bike.value);
    document.getElementById("filter-bike-val").textContent = `${bike.value} min`;
    render();
  });
  document.getElementById("filter-reset").addEventListener("click", () => {
    state.filters = { type: "", venueId: "", maxBike: 20 };
    bike.value = 20;
    document.getElementById("filter-bike-val").textContent = "20 min";
    renderFilters();
    render();
  });

  document.getElementById("add-form").addEventListener("submit", async e => {
    e.preventDefault();
    const body = {
      title: document.getElementById("f-title").value,
      type: document.getElementById("f-type").value,
      venue_id: Number(document.getElementById("f-venue").value),
      date: document.getElementById("f-date").value,
      time: document.getElementById("f-time").value,
      description: document.getElementById("f-desc").value,
    };
    try {
      await api("/api/events", { method: "POST", body });
      e.target.reset();
      document.getElementById("f-time").value = "20:30";
      const d = body.date;
      if (d && !d.startsWith(state.month)) state.month = d.slice(0, 7);
      await reloadEvents();
    } catch (err) {
      alert(err.message);
    }
  });
}

bind();
loadAll().catch(err => {
  document.getElementById("event-list").innerHTML =
    `<p class="empty-msg">Impossible de contacter l'API : ${esc(err.message)}</p>`;
});
