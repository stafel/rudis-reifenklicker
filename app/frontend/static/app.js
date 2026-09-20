"use strict";

const cfg = window.APP_CONFIG || {};
const apiBase = cfg.apiBase || "";
const pollMs = cfg.pollMs || 2000;

const $ = (id) => document.getElementById(id);
const wheel = $("wheel");
const countEl = $("count");

let currentCount = 0;
let displayedCount = 0;
let countAnimation = null;

const numberFormat = new Intl.NumberFormat("de-CH");

function setConnection(ok) {
  const badge = $("connection-badge");
  badge.textContent = ok ? "verbunden" : "offline";
  badge.classList.toggle("offline", !ok);
}

function animateCount(to) {
  currentCount = to;
  if (countAnimation) cancelAnimationFrame(countAnimation);
  const from = displayedCount;
  const start = performance.now();
  const duration = 350;

  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    displayedCount = Math.round(from + (to - from) * (1 - Math.pow(1 - t, 3)));
    countEl.textContent = numberFormat.format(displayedCount);
    if (t < 1) countAnimation = requestAnimationFrame(step);
  };
  countAnimation = requestAnimationFrame(step);
}

function render(state) {
  animateCount(state.count ?? 0);
  $("version-badge").textContent = `Version ${state.version ?? "?"}`;
  $("pod-badge").textContent = `Pod ${state.pod ?? "?"}`;
  $("golden-flag").textContent = `Goldfelge: ${state.goldenRim ? "an" : "aus"}`;
  $("season-badge").textContent = state.season ?? state.version ?? "unbekannt";
  document.body.dataset.version = state.version ?? "";
  wheel.classList.toggle("gold", Boolean(state.goldenRim));
  $("golden-note").hidden = !state.goldenRim;
}

async function fetchState() {
  const response = await fetch(`${apiBase}/api/count`, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refresh() {
  try {
    render(await fetchState());
    setConnection(true);
  } catch (err) {
    setConnection(false);
  }
}

function floatText(text, golden) {
  const rect = wheel.getBoundingClientRect();
  const el = document.createElement("span");
  el.className = "floating" + (golden ? " golden" : "");
  el.textContent = text;
  el.style.left = `${rect.left + rect.width / 2}px`;
  el.style.top = `${rect.top + rect.height / 2}px`;
  document.body.appendChild(el);
  el.addEventListener("animationend", () => el.remove());
}

function spin() {
  wheel.classList.remove("spin");
  // Reflow erzwingen, damit die Animation erneut startet.
  void wheel.offsetWidth;
  wheel.classList.add("spin");
}

wheel.addEventListener("click", async () => {
  spin();
  try {
    const response = await fetch(`${apiBase}/api/click`, { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const state = await response.json();
    render(state);
    floatText(`+${state.delta ?? 1}`, state.golden);
    setConnection(true);
  } catch (err) {
    setConnection(false);
  }
});

refresh();
setInterval(refresh, pollMs);
