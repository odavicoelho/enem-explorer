// ENEM Explorer: a tiny hash-routed app over pre-computed JSON. No framework, no build step.
"use strict";

const app = document.getElementById("app");
const AREAS = [
  ["avg_languages", "Linguagens"],
  ["avg_humanities", "Ciências Humanas"],
  ["avg_natural_sciences", "Ciências da Natureza"],
  ["avg_math", "Matemática"],
  ["avg_essay", "Redação"],
];
const AREA_NAMES = { LC: "Linguagens", CH: "Ciências Humanas", CN: "Ciências da Natureza", MT: "Matemática" };
const TYPES = { F: "Federal", E: "Estadual", M: "Municipal", P: "Privada" };
const cache = new Map();

// ---------- helpers ----------
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const fmt = (n, d = 1) => (n == null ? "—" : Number(n).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const int = (n) => (n == null ? "—" : Number(n).toLocaleString("pt-BR"));
const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const title = (s) => String(s ?? "").toLowerCase().replace(/(^|\s|\/|-)(\p{L})/gu, (m, a, b) => a + b.toUpperCase());

async function load(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(`data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${path}`);
      return r.json();
    }));
  }
  return cache.get(path);
}

function bar(value, max = 1000, cls = "") {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return `<div class="bar ${cls}"><span style="width:${pct.toFixed(1)}%"></span></div>`;
}

function setTitle(text) {
  document.title = `${text} · ENEM Explorer`;
}

// ---------- pages ----------
async function home() {
  const o = await load("overview.json");
  setTitle("Resultados do ENEM 2024 por escola, cidade e estado");
  const types = o.school_types;
  const max = Math.max(...types.map((t) => t.avg_overall));
  app.innerHTML = `
    <h1>Como cada escola do Brasil foi no ENEM 2024</h1>
    <p class="muted">Médias de ${int(o.totals.students)} alunos concluintes do ensino médio em ${int(o.totals.schools)} escolas,
      e as habilidades que eles mais erraram. Busque uma escola ou cidade no topo da página.</p>

    <h2>Pública ou privada?</h2>
    <div class="card bars">
      ${types.map((t) => `
        <div class="bar-row"><span>${esc(t.school_type)}</span>${bar(t.avg_overall, max * 1.1)}<span class="num">${fmt(t.avg_overall)}</span></div>`).join("")}
      <p class="muted small" style="margin:4px 0 0">Média geral (as 4 provas + redação). Rede estadual: ${int(types.find((t) => t.school_type === "Estadual")?.students)} alunos.</p>
    </div>

    <h2>As habilidades mais erradas no Brasil</h2>
    <div class="tabs" role="tablist">${types.map((t, i) => `<button role="tab" data-type="${esc(t.school_type)}" aria-selected="${i === types.length - 1}">${esc(t.school_type)}</button>`).join("")}</div>
    <div id="skills"></div>

    <h2>Estados</h2>
    <div class="card table-wrap"><table>
      <tr><th>#</th><th>Estado</th><th class="num">Escolas</th><th class="num">Alunos</th><th class="num">Matemática</th><th class="num">Redação</th><th class="num">Média geral</th></tr>
      ${o.states.map((s, i) => `<tr><td>${i + 1}</td><td><a href="#/uf/${esc(s.state)}">${esc(s.state)}</a></td>
        <td class="num">${int(s.schools)}</td><td class="num">${int(s.students)}</td><td class="num">${fmt(s.avg_math)}</td>
        <td class="num">${fmt(s.avg_essay)}</td><td class="num"><b>${fmt(s.avg_overall)}</b></td></tr>`).join("")}
    </table></div>`;

  const showSkills = (type) => {
    const rows = o.hardest_skills.filter((s) => s.school_type === type);
    document.getElementById("skills").innerHTML = skillTable(rows);
    app.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.type === type));
  };
  app.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => showSkills(b.dataset.type)));
  showSkills(types[types.length - 1].school_type);
}

function skillTable(rows) {
  return `<div class="card skills">${rows.map((s) => `
    <div class="skill">
      <div class="skill-head"><span class="muted small">${esc(AREA_NAMES[s.area])} · H${esc(s.skill)}</span>
        <span class="num"><b>${fmt(s.pct_correct)}%</b> <span class="muted small">de acertos</span></span></div>
      <div>${esc(s.skill_description)}</div>
    </div>`).join("")}</div>`;
}

async function statePage(uf) {
  const d = await load(`states/${uf}.json`);
  setTitle(`ENEM 2024 em ${uf}`);
  const s = d.state;
  const cols = d.ranking.columns;
  const rows = d.ranking.rows.map((r) => Object.fromEntries(cols.map((c, i) => [c, r[i]])));
  const maxType = Math.max(...d.school_types.map((t) => t.avg_overall));
  app.innerHTML = `
    <p class="muted"><a href="#/">Brasil</a> › ${esc(uf)}</p>
    <h1>ENEM 2024 em ${esc(uf)}</h1>
    <div class="grid">
      <div class="card stat"><span class="muted">Média geral</span><b>${fmt(s.avg_overall)}</b></div>
      <div class="card stat"><span class="muted">Escolas</span><b>${int(s.schools)}</b></div>
      <div class="card stat"><span class="muted">Alunos</span><b>${int(s.students)}</b></div>
      <div class="card stat"><span class="muted">Matemática</span><b>${fmt(s.avg_math)}</b></div>
    </div>

    <h2>Por tipo de escola</h2>
    <div class="card bars">${d.school_types.map((t) => `
      <div class="bar-row"><span>${esc(t.school_type)}</span>${bar(t.avg_overall, maxType * 1.1)}<span class="num">${fmt(t.avg_overall)}</span></div>`).join("")}
    </div>

    <h2>Escolas</h2>
    <input class="filter" id="school-filter" placeholder="Filtrar por nome ou cidade…" aria-label="Filtrar escolas">
    <div class="card table-wrap"><table id="ranking"></table></div>
    <p class="muted small" id="ranking-note"></p>

    <h2>Cidades</h2>
    <div class="card table-wrap"><table>
      <tr><th>#</th><th>Cidade</th><th class="num">Escolas</th><th class="num">Alunos</th><th class="num">Média geral</th></tr>
      ${d.cities.slice(0, 30).map((c) => `<tr><td>${c.rank_in_state}</td><td>${esc(c.city)}</td><td class="num">${int(c.schools)}</td>
        <td class="num">${int(c.students)}</td><td class="num"><b>${fmt(c.avg_overall)}</b></td></tr>`).join("")}
    </table></div>
    ${d.cities.length > 30 ? `<p class="muted small">Mostrando as 30 primeiras de ${d.cities.length} cidades.</p>` : ""}

    <h2>Habilidades mais erradas em ${esc(uf)}</h2>
    <div class="tabs" role="tablist">${d.school_types.map((t) => `<button role="tab" data-type="${esc(t.school_type)}">${esc(t.school_type)}</button>`).join("")}</div>
    <div id="skills"></div>`;

  const table = document.getElementById("ranking");
  const render = (q) => {
    const f = fold(q);
    const hits = f ? rows.filter((r) => fold(`${r.school_name} ${r.city}`).includes(f)) : rows;
    table.innerHTML = `<tr><th>#</th><th>Escola</th><th>Cidade</th><th>Tipo</th><th class="num">Alunos</th><th class="num">Média geral</th></tr>
      ${hits.slice(0, 50).map((r) => `<tr><td>${r.rank_in_state}</td><td><a href="#/escola/${r.school_id}">${esc(title(r.school_name))}</a></td>
        <td>${esc(r.city)}</td><td>${esc(TYPES[r.school_type])}</td><td class="num">${int(r.students)}</td><td class="num"><b>${fmt(r.avg_overall)}</b></td></tr>`).join("")}`;
    document.getElementById("ranking-note").textContent =
      hits.length > 50 ? `Mostrando 50 de ${int(hits.length)} escolas. Use o filtro para encontrar outras.` : "";
  };
  document.getElementById("school-filter").addEventListener("input", (e) => render(e.target.value));
  render("");

  const showSkills = (type) => {
    document.getElementById("skills").innerHTML = skillTable(d.hardest_skills.filter((x) => x.school_type === type));
    app.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.type === type));
  };
  app.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => showSkills(b.dataset.type)));
  const preferred = d.school_types.find((t) => t.school_type === "Estadual") ?? d.school_types[0];
  if (preferred) showSkills(preferred.school_type);
}

async function schoolPage(id) {
  const s = await load(`schools/${id}.json`);
  const name = title(s.school_name);
  setTitle(name);
  const below = s.weakest_skills.filter((r) => r.gap_vs_benchmark < 0);
  const c = s.compare;
  const facilities = [
    [s.has_internet, "Internet"],
    [s.has_library, "Biblioteca"],
    [s.has_science_lab, "Laboratório de ciências"],
  ];
  const series = [
    ["Esta escola", s, ""],
    [`${s.city}`, c.city, "alt"],
    [`Média ${s.state}`, c.state, "dim"],
  ];
  app.innerHTML = `
    <p class="muted"><a href="#/">Brasil</a> › <a href="#/uf/${esc(s.state)}">${esc(s.state)}</a> › ${esc(s.city)}</p>
    <h1>${esc(name)}</h1>
    <p>
      <span class="pill">${esc(s.school_type)}</span><span class="pill">${esc(s.school_location ?? "")}</span>
      ${s.neighborhood ? `<span class="pill">${esc(title(s.neighborhood))}</span>` : ""}
      ${facilities.filter(([has]) => has).map(([, label]) => `<span class="pill">✓ ${label}</span>`).join("")}
    </p>
    <div class="grid">
      <div class="card stat"><span class="muted">Média geral</span><b>${fmt(s.avg_overall)}</b></div>
      <div class="card stat"><span class="muted">No estado</span><b>${int(s.rank_in_state)}º</b><span class="muted small">de ${int(s.schools_in_state)}</span></div>
      <div class="card stat"><span class="muted">Entre escolas ${esc(s.school_type.toLowerCase())}s de ${esc(s.state)}</span><b>${int(s.rank_in_state_and_type)}º</b><span class="muted small">de ${int(s.schools_in_state_and_type)}</span></div>
      <div class="card stat"><span class="muted">Melhor que</span><b>${fmt(s.national_percentile, 0)}%</b><span class="muted small">das escolas do Brasil</span></div>
    </div>
    <p class="muted small">${int(s.students)} alunos concluintes fizeram todas as provas.</p>

    <h2>Notas por área</h2>
    <div class="legend">${series.map(([label, , cls]) => `<span><i style="background:var(${cls === "alt" ? "--accent-2" : cls === "dim" ? "--muted" : "--accent"})"></i>${esc(label)}</span>`).join("")}</div>
    <div class="card bars compare">
      ${AREAS.map(([key, label]) => `
        <div><b class="small">${label}</b>
        ${series.map(([, data, cls]) => `<div class="bar-row"><span class="muted small"></span>${bar(data?.[key] ?? 0, 1000, cls)}<span class="num small">${fmt(data?.[key])}</span></div>`).join("")}
        </div>`).join("")}
    </div>

    <h2>Onde a escola fica abaixo de escolas parecidas</h2>
    <p class="muted">Comparação com escolas ${esc(s.school_type.toLowerCase())}s de ${esc(s.state)}, habilidade por habilidade.</p>
    ${below.length ? gapTable(below)
      : `<p class="card">Em todas as habilidades, esta escola acerta mais que a média de escolas ${esc(s.school_type.toLowerCase())}s de ${esc(s.state)}. 🎉</p>`}
    ${s.strongest_skills.length ? `
    <h2>Onde a escola se destaca</h2>
    ${gapTable(s.strongest_skills)}` : ""}`;
}

function gapTable(rows) {
  return `<div class="card skills">${rows.map((r) => `
    <div class="skill">
      <div class="skill-head"><span class="muted small">${esc(AREA_NAMES[r.area])} · H${esc(r.skill)}</span>
        <span class="num ${r.gap_vs_benchmark < 0 ? "bad" : "good"}"><b>${r.gap_vs_benchmark > 0 ? "+" : ""}${fmt(r.gap_vs_benchmark)} p.p.</b></span></div>
      <div>${esc(r.skill_description)}</div>
      <div class="muted small">Escola: ${fmt(r.pct_correct)}% de acertos · escolas parecidas: ${fmt(r.benchmark_pct_correct)}%</div>
    </div>`).join("")}</div>`;
}

// ---------- search ----------
const input = document.getElementById("search");
const results = document.getElementById("results");
let index = null;

async function ensureIndex() {
  if (!index) {
    const data = await load("schools-index.json");
    index = data.rows.map(([id, name, city, uf, type, overall]) => ({
      id, name, city, uf, type, overall, key: fold(`${name} ${city} ${uf}`),
    }));
  }
  return index;
}

input.addEventListener("focus", ensureIndex, { once: true });
input.addEventListener("input", async () => {
  const q = fold(input.value.trim());
  if (q.length < 2) { results.hidden = true; return; }
  const words = q.split(/\s+/);
  const hits = (await ensureIndex()).filter((s) => words.every((w) => s.key.includes(w))).slice(0, 20);
  results.innerHTML = hits.length
    ? hits.map((s) => `<li><a href="#/escola/${s.id}">${esc(title(s.name))}<br><span class="muted small">${esc(s.city)} · ${esc(s.uf)} · ${TYPES[s.type]} · média ${fmt(s.overall)}</span></a></li>`).join("")
    : `<li class="muted small" style="padding:8px 10px">Nenhuma escola encontrada (só aparecem escolas com 10+ alunos).</li>`;
  results.hidden = false;
});
results.addEventListener("click", () => { results.hidden = true; input.value = ""; });
document.addEventListener("click", (e) => { if (!e.target.closest(".search")) results.hidden = true; });

// ---------- router ----------
async function route() {
  const [, page, arg] = location.hash.split("/");
  window.scrollTo(0, 0);
  try {
    if (page === "uf" && /^[A-Z]{2}$/.test(arg)) await statePage(arg);
    else if (page === "escola" && /^\d+$/.test(arg)) await schoolPage(arg);
    else await home();
  } catch (err) {
    console.error(err);
    app.innerHTML = `<h1>Página não encontrada</h1><p class="muted">Essa escola ou estado não está nos dados publicados.</p><p><a href="#/">Voltar ao início</a></p>`;
  }
}
window.addEventListener("hashchange", route);
route();
