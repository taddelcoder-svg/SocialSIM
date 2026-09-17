// Rahmen-UI: baut ein Szenario-JSON per Klick zusammen (kein Freitext-JSON noetig,
// ausser bei den seltenen Feldern "options"/"weights" einer diskreten Verteilung).
// Das erzeugte Objekt hat exakt die Form von scenarios/*.json - derselbe Code
// (config.py, model.py) verarbeitet es serverseitig ueber /api/run.

const NETWORK_FIELDS = {
  watts_strogatz: [
    { key: "k", label: "Nachbarn pro Knoten (k)", type: "number", default: 4 },
    { key: "beta", label: "Rewiring-Wahrscheinlichkeit (beta)", type: "number", step: 0.01, default: 0.1 },
  ],
  barabasi_albert: [{ key: "m", label: "neue Kanten pro Knoten (m)", type: "number", default: 3 }],
  erdos_renyi: [{ key: "p", label: "Verbindungswahrscheinlichkeit (p)", type: "number", step: 0.01, default: 0.05 }],
  grid: [
    { key: "side", label: "Seitenlaenge (leer = automatisch)", type: "number", optional: true },
    { key: "periodic", label: "periodisch (Torus)", type: "checkbox", default: true },
  ],
  complete: [],
};

const MECHANIC_FIELDS = {
  bounded_confidence: [
    { key: "epsilon", label: "Vertrauensradius (epsilon)", type: "number", step: 0.01, default: 0.2 },
    { key: "mu", label: "Anpassungsrate (mu)", type: "number", step: 0.01, default: 1.0 },
  ],
  threshold: [{ key: "threshold_key", label: "Attributname fuer Schwellenwert", type: "text", default: "threshold" }],
  degroot: [
    { key: "self_weight", label: "Selbstgewicht", type: "number", step: 0.01, default: 0.5 },
    { key: "credibility_key", label: "Attribut fuer Glaubwuerdigkeit (leer = keins)", type: "text", optional: true },
  ],
};

const DISTRIBUTION_FIELDS = {
  normal: [
    { key: "mean", label: "Mittelwert", type: "number", default: 0 },
    { key: "std", label: "Streuung", type: "number", default: 1 },
    { key: "min", label: "Minimum (optional)", type: "number", optional: true },
    { key: "max", label: "Maximum (optional)", type: "number", optional: true },
  ],
  uniform: [
    { key: "min", label: "Minimum", type: "number", default: 0 },
    { key: "max", label: "Maximum", type: "number", default: 1 },
  ],
  beta: [
    { key: "a", label: "Formparameter a", type: "number", default: 2 },
    { key: "b", label: "Formparameter b", type: "number", default: 2 },
    { key: "min", label: "Minimum", type: "number", default: 0 },
    { key: "max", label: "Maximum", type: "number", default: 1 },
  ],
  constant: [{ key: "value", label: "Wert", type: "number", default: 0 }],
  choice: [
    { key: "options", label: "Optionen (Komma-getrennt, z.B. 0,1)", type: "text", default: "0,1" },
    { key: "weights", label: "Gewichte (optional, z.B. 0.9,0.1)", type: "text", optional: true },
  ],
};

const EVENT_FIELDS = {
  narrow_confidence: [
    { key: "factor", label: "Faktor (z.B. 0.3 = 70% enger)", type: "number", step: 0.01, default: 0.5 },
    { key: "duration", label: "Dauer (Ticks)", type: "number", default: 10 },
    { key: "target", label: "Ziel-Mechanik bei mehreren (leer = automatisch)", type: "text", optional: true },
  ],
  shift_opinion: [
    { key: "delta", label: "Verschiebung (delta)", type: "number", step: 0.01, default: 0.0 },
    { key: "fraction", label: "Anteil betroffener Agenten", type: "number", step: 0.01, default: 1.0 },
  ],
};

let rowCounter = 0;

function fieldInputHtml(field, idPrefix, value) {
  const val = value !== undefined ? value : field.default;
  const id = `${idPrefix}-${field.key}`;
  if (field.type === "checkbox") {
    const checked = val ? "checked" : "";
    return `<div class="field-group"><label>${field.label}</label>
      <input type="checkbox" id="${id}" data-key="${field.key}" ${checked} /></div>`;
  }
  const step = field.step !== undefined ? `step="${field.step}"` : "";
  const placeholder = val === undefined || val === null ? "" : `value="${val}"`;
  return `<div class="field-group"><label>${field.label}</label>
    <input type="${field.type}" id="${id}" data-key="${field.key}" ${step} ${placeholder} /></div>`;
}

function renderFields(container, spec, idPrefix, values = {}) {
  container.innerHTML = spec.map((f) => fieldInputHtml(f, idPrefix, values[f.key])).join("");
}

function readFields(container, spec) {
  const out = {};
  for (const field of spec) {
    const el = container.querySelector(`[data-key="${field.key}"]`);
    if (!el) continue;
    if (field.type === "checkbox") {
      out[field.key] = el.checked;
      continue;
    }
    const raw = el.value;
    if (raw === "" || raw === null) {
      if (!field.optional) out[field.key] = field.default;
      continue;
    }
    if (field.key === "options" || field.key === "weights") {
      out[field.key] = raw.split(",").map((s) => parseFloat(s.trim()));
    } else if (field.type === "number") {
      out[field.key] = parseFloat(raw);
    } else {
      out[field.key] = raw;
    }
  }
  return out;
}

// "histogram" ist eine variable Liste von Bins ({min,max,weight}) statt fester
// Felder - wird deshalb separat vom generischen Feld-Renderer behandelt.
function renderHistogramBins(container, bins) {
  const rows = bins && bins.length ? bins : [{ min: 0, max: 1, weight: 1 }];
  container.innerHTML = `<div class="hist-bins"></div><button type="button" class="add-bin secondary">+ Bin</button>`;
  const binsEl = container.querySelector(".hist-bins");

  function addBinRow(bin) {
    const row = document.createElement("div");
    row.className = "row-fields hist-bin-row";
    row.innerHTML = `
      <input type="number" class="bin-min" value="${bin.min}" placeholder="min" step="0.01" />
      <input type="number" class="bin-max" value="${bin.max}" placeholder="max" step="0.01" />
      <input type="number" class="bin-weight" value="${bin.weight}" placeholder="Gewicht" step="0.01" />
      <button type="button" class="remove-row" title="entfernen">&times;</button>
    `;
    row.querySelector(".remove-row").addEventListener("click", () => {
      if (binsEl.querySelectorAll(".hist-bin-row").length > 1) row.remove();
    });
    binsEl.appendChild(row);
  }

  rows.forEach(addBinRow);
  container.querySelector(".add-bin").addEventListener("click", () => addBinRow({ min: 0, max: 1, weight: 1 }));
}

function readHistogramBins(container) {
  const bins = [];
  container.querySelectorAll(".hist-bin-row").forEach((row) => {
    bins.push({
      min: parseFloat(row.querySelector(".bin-min").value),
      max: parseFloat(row.querySelector(".bin-max").value),
      weight: parseFloat(row.querySelector(".bin-weight").value),
    });
  });
  return bins;
}

function renderDistributionParams(container, kind, idPrefix, values = {}) {
  if (kind === "histogram") {
    renderHistogramBins(container, values.bins);
  } else {
    renderFields(container, DISTRIBUTION_FIELDS[kind], idPrefix, values);
  }
}

function readDistributionParams(container, kind) {
  if (kind === "histogram") {
    return { bins: readHistogramBins(container) };
  }
  return readFields(container, DISTRIBUTION_FIELDS[kind]);
}

function readDistribution(kindSelect, paramsContainer) {
  const kind = kindSelect.value;
  return { kind, params: readDistributionParams(paramsContainer, kind) };
}

function setDistribution(kindSelect, paramsContainer, dist) {
  kindSelect.value = dist.kind;
  renderDistributionParams(paramsContainer, dist.kind, paramsContainer.id, dist.params || {});
}

// ---- Netzwerk ----
const networkTypeSelect = document.getElementById("network-type");
const networkParamsEl = document.getElementById("network-params");
function refreshNetworkFields(values = {}) {
  renderFields(networkParamsEl, NETWORK_FIELDS[networkTypeSelect.value], "net", values);
}
networkTypeSelect.addEventListener("change", () => refreshNetworkFields());
refreshNetworkFields();

// ---- Ausgangszustand ----
const opinionKindSelect = document.getElementById("opinion-kind");
const opinionParamsEl = document.getElementById("opinion-params");
opinionKindSelect.addEventListener("change", () =>
  renderDistributionParams(opinionParamsEl, opinionKindSelect.value, "op")
);
renderDistributionParams(opinionParamsEl, opinionKindSelect.value, "op");

// ---- Mechanik (eine oder mehrere, in Ausfuehrungsreihenfolge) ----
const MECHANIC_LABELS = {
  bounded_confidence: "Bounded Confidence (Hegselmann-Krause)",
  threshold: "Schwellenwertmodell (Granovetter)",
  degroot: "DeGroot-Lernen",
};
const mechanicList = document.getElementById("mechanic-list");

function addMechanicRow(model = "bounded_confidence", params = {}) {
  const rowId = `mech-${rowCounter++}`;
  const row = document.createElement("div");
  row.className = "dynamic-row";
  row.innerHTML = `
    <button type="button" class="remove-row" title="entfernen">&times;</button>
    <div class="field-group">
      <label>Modell</label>
      <select class="mech-model">
        ${Object.entries(MECHANIC_LABELS).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
      </select>
    </div>
    <div class="row-fields mech-params"></div>
  `;
  mechanicList.appendChild(row);
  const modelSelect = row.querySelector(".mech-model");
  const paramsEl = row.querySelector(".mech-params");
  modelSelect.value = model;
  renderFields(paramsEl, MECHANIC_FIELDS[modelSelect.value], rowId, params);
  modelSelect.addEventListener("change", () => renderFields(paramsEl, MECHANIC_FIELDS[modelSelect.value], rowId));
  row.querySelector(".remove-row").addEventListener("click", () => {
    if (mechanicList.querySelectorAll(".dynamic-row").length > 1) row.remove();
  });
}

document.getElementById("add-mechanic").addEventListener("click", () => addMechanicRow());

function readMechanics() {
  const out = [];
  mechanicList.querySelectorAll(".dynamic-row").forEach((row) => {
    const modelSelect = row.querySelector(".mech-model");
    const paramsEl = row.querySelector(".mech-params");
    out.push({ model: modelSelect.value, params: readFields(paramsEl, MECHANIC_FIELDS[modelSelect.value]) });
  });
  return out;
}

// ---- Attribute (Population) ----
const attributeList = document.getElementById("attribute-list");

function addAttributeRow(name = "", dist = { kind: "normal", params: {} }) {
  const rowId = `attr-${rowCounter++}`;
  const row = document.createElement("div");
  row.className = "dynamic-row";
  row.dataset.rowId = rowId;
  row.innerHTML = `
    <button type="button" class="remove-row" title="entfernen">&times;</button>
    <div class="field-group">
      <label>Attributname</label>
      <input type="text" class="attr-name" value="${name}" placeholder="z.B. threshold, credibility, age" />
    </div>
    <div class="field-group">
      <label>Verteilung</label>
      <select class="attr-kind">
        <option value="normal">Normalverteilt</option>
        <option value="uniform">Gleichverteilt</option>
        <option value="beta">Beta</option>
        <option value="choice">Diskret</option>
        <option value="constant">Konstant</option>
        <option value="histogram">Histogramm (reale Bins)</option>
      </select>
    </div>
    <div class="row-fields attr-params"></div>
  `;
  attributeList.appendChild(row);
  const kindSelect = row.querySelector(".attr-kind");
  const paramsEl = row.querySelector(".attr-params");
  kindSelect.value = dist.kind;
  renderDistributionParams(paramsEl, kindSelect.value, rowId, dist.params || {});
  kindSelect.addEventListener("change", () => renderDistributionParams(paramsEl, kindSelect.value, rowId));
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
}

document.getElementById("add-attribute").addEventListener("click", () => addAttributeRow());

function readAttributes() {
  const out = {};
  attributeList.querySelectorAll(".dynamic-row").forEach((row) => {
    const name = row.querySelector(".attr-name").value.trim();
    if (!name) return;
    const kindSelect = row.querySelector(".attr-kind");
    const paramsEl = row.querySelector(".attr-params");
    out[name] = { kind: kindSelect.value, params: readDistributionParams(paramsEl, kindSelect.value) };
  });
  return out;
}

// ---- Ereignisse ----
const eventList = document.getElementById("event-list");

function addEventRow(tick = 10, type = "shift_opinion", params = {}) {
  const rowId = `evt-${rowCounter++}`;
  const row = document.createElement("div");
  row.className = "dynamic-row";
  row.innerHTML = `
    <button type="button" class="remove-row" title="entfernen">&times;</button>
    <div class="field-group">
      <label>Tick</label>
      <input type="number" class="evt-tick" value="${tick}" />
    </div>
    <div class="field-group">
      <label>Typ</label>
      <select class="evt-type">
        <option value="shift_opinion">Meinungsschock (shift_opinion)</option>
        <option value="narrow_confidence">Konfidenz verengen (narrow_confidence)</option>
      </select>
    </div>
    <div class="row-fields evt-params"></div>
  `;
  eventList.appendChild(row);
  const typeSelect = row.querySelector(".evt-type");
  const paramsEl = row.querySelector(".evt-params");
  typeSelect.value = type;
  renderFields(paramsEl, EVENT_FIELDS[typeSelect.value], rowId, params);
  typeSelect.addEventListener("change", () => renderFields(paramsEl, EVENT_FIELDS[typeSelect.value], rowId));
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
}

document.getElementById("add-event").addEventListener("click", () => addEventRow());

function readEvents() {
  const out = [];
  eventList.querySelectorAll(".dynamic-row").forEach((row) => {
    const tick = parseInt(row.querySelector(".evt-tick").value, 10);
    const typeSelect = row.querySelector(".evt-type");
    const paramsEl = row.querySelector(".evt-params");
    out.push({ tick, type: typeSelect.value, params: readFields(paramsEl, EVENT_FIELDS[typeSelect.value]) });
  });
  return out;
}

// ---- Config bauen / laden ----
function buildConfig() {
  const seedRaw = document.getElementById("seed").value;
  return {
    name: "Rahmen-UI Szenario",
    population: {
      size: parseInt(document.getElementById("pop-size").value, 10),
      attributes: readAttributes(),
    },
    network: { type: networkTypeSelect.value, params: readFields(networkParamsEl, NETWORK_FIELDS[networkTypeSelect.value]) },
    initial_state: {
      opinion: {
        ...readDistribution(opinionKindSelect, opinionParamsEl),
        ...(document.getElementById("opinion-source").value
          ? { source: document.getElementById("opinion-source").value }
          : {}),
      },
    },
    mechanics: readMechanics(),
    events: readEvents(),
    time: {
      steps: parseInt(document.getElementById("time-steps").value, 10),
      runs: parseInt(document.getElementById("time-runs").value, 10),
    },
    seed: seedRaw === "" ? null : parseInt(seedRaw, 10),
  };
}

function loadConfigIntoForm(config) {
  document.getElementById("pop-size").value = config.population.size;
  attributeList.innerHTML = "";
  Object.entries(config.population.attributes || {}).forEach(([name, dist]) => addAttributeRow(name, dist));

  networkTypeSelect.value = config.network.type;
  refreshNetworkFields(config.network.params || {});

  const opinion = config.initial_state.opinion;
  setDistribution(opinionKindSelect, opinionParamsEl, opinion);
  document.getElementById("opinion-source").value = opinion.source || "";

  mechanicList.innerHTML = "";
  const mechanics = Array.isArray(config.mechanics) ? config.mechanics : [config.mechanics];
  mechanics.forEach((m) => addMechanicRow(m.model, m.params || {}));

  eventList.innerHTML = "";
  (config.events || []).forEach((evt) => addEventRow(evt.tick, evt.type, evt.params || {}));

  document.getElementById("time-steps").value = config.time?.steps ?? 50;
  document.getElementById("time-runs").value = config.time?.runs ?? 1;
  document.getElementById("seed").value = config.seed ?? "";
}

// ---- Beispiele laden ----
const exampleSelect = document.getElementById("example-select");
let loadedExamples = [];

fetch("/api/examples")
  .then((r) => r.json())
  .then((examples) => {
    loadedExamples = examples;
    examples.forEach((ex, i) => {
      const config = JSON.parse(ex.config);
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = config.name || ex.file;
      exampleSelect.appendChild(opt);
    });
  })
  .catch(() => {
    // Keine Beispiele erreichbar - Formular bleibt leer nutzbar.
  });

exampleSelect.addEventListener("change", () => {
  if (exampleSelect.value === "") return;
  const config = JSON.parse(loadedExamples[parseInt(exampleSelect.value, 10)].config);
  loadConfigIntoForm(config);
});

// ---- Simulation starten ----
const errorBox = document.getElementById("error-box");
const resultSummary = document.getElementById("result-summary");
const configPreview = document.getElementById("config-preview");
let chart = null;

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

document.getElementById("run-button").addEventListener("click", async () => {
  clearError();
  let config;
  try {
    config = buildConfig();
  } catch (err) {
    showError(`Formular fehlerhaft: ${err.message}`);
    return;
  }
  configPreview.textContent = JSON.stringify(config, null, 2);
  resultSummary.textContent = "Simulation laeuft ...";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Unbekannter Fehler");
      resultSummary.textContent = "Simulation fehlgeschlagen.";
      return;
    }
    renderChart(data);
    resultSummary.textContent =
      `${data.population_size} Agenten, Mechanik "${data.mechanic}", ` +
      `gemittelt ueber ${data.runs} Lauf/Laeufe. ` +
      `Meinungsstreuung: ${data.std_opinion[0].toFixed(3)} -> ${data.std_opinion[data.std_opinion.length - 1].toFixed(3)}.`;
  } catch (err) {
    showError(`Verbindung zum Server fehlgeschlagen: ${err.message}`);
    resultSummary.textContent = "Simulation fehlgeschlagen.";
  }
});

document.getElementById("export-button").addEventListener("click", () => {
  let config;
  try {
    config = buildConfig();
  } catch (err) {
    showError(`Formular fehlerhaft: ${err.message}`);
    return;
  }
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "szenario.json";
  a.click();
  URL.revokeObjectURL(url);
});

// ---- Kalibrierung pruefen ----
const calibrationBox = document.getElementById("calibration-box");
const calibrationTable = document.getElementById("calibration-table");

document.getElementById("calibrate-button").addEventListener("click", async () => {
  clearError();
  let config;
  try {
    config = buildConfig();
  } catch (err) {
    showError(`Formular fehlerhaft: ${err.message}`);
    return;
  }

  try {
    const response = await fetch("/api/calibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Unbekannter Fehler");
      return;
    }
    renderCalibrationTable(data);
  } catch (err) {
    showError(`Verbindung zum Server fehlgeschlagen: ${err.message}`);
  }
});

function renderCalibrationTable(results) {
  if (results.length === 0) {
    calibrationTable.innerHTML = "<tr><td>Keine Attribute/Ausgangswerte zum Pruefen konfiguriert.</td></tr>";
  } else {
    const rows = results
      .map(
        (r) => `
      <tr>
        <td>${r.field}</td>
        <td>${r.kind}</td>
        <td class="${r.ok ? "calib-status-ok" : "calib-status-bad"}">${r.ok ? "OK" : "Abweichung"}</td>
        <td>${r.detail}</td>
      </tr>`
      )
      .join("");
    calibrationTable.innerHTML = `<tr><th>Feld</th><th>Verteilung</th><th>Status</th><th>Details (Ziel vs. gezogen)</th></tr>${rows}`;
  }
  calibrationBox.classList.remove("hidden");
}

// ---- Sensitivitaetsanalyse ----
const sensitivityBox = document.getElementById("sensitivity-box");
const sensitivitySummary = document.getElementById("sensitivity-summary");
let sensitivityChart = null;

document.getElementById("sensitivity-button").addEventListener("click", async () => {
  clearError();
  let config;
  try {
    config = buildConfig();
  } catch (err) {
    showError(`Formular fehlerhaft: ${err.message}`);
    return;
  }

  const parameter = document.getElementById("sens-param").value.trim();
  const metric = document.getElementById("sens-metric").value;
  const values = document
    .getElementById("sens-values")
    .value.split(",")
    .map((v) => v.trim())
    .filter((v) => v.length)
    .map((v) => (isNaN(parseFloat(v)) ? v : parseFloat(v)));

  if (!parameter || values.length === 0) {
    showError("Sensitivitaetsanalyse braucht einen Parameterpfad und mindestens einen Wert.");
    return;
  }

  sensitivitySummary.textContent = "Analyse laeuft ...";
  sensitivityBox.classList.remove("hidden");

  try {
    const response = await fetch("/api/sensitivity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config, parameter, values, metric }),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Unbekannter Fehler");
      sensitivitySummary.textContent = "Analyse fehlgeschlagen.";
      return;
    }
    renderSensitivityChart(data, parameter);
    const spread = Math.max(...data.mean) - Math.min(...data.mean);
    sensitivitySummary.textContent =
      `Spannweite von "${data.metric}" ueber ${data.values.length} Werte von "${parameter}": ${spread.toFixed(4)}.`;
  } catch (err) {
    showError(`Verbindung zum Server fehlgeschlagen: ${err.message}`);
    sensitivitySummary.textContent = "Analyse fehlgeschlagen.";
  }
});

function renderSensitivityChart(data, parameter) {
  const ctx = document.getElementById("sensitivity-chart");
  if (sensitivityChart) sensitivityChart.destroy();
  sensitivityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.values,
      datasets: [
        {
          label: data.metric,
          data: data.mean,
          borderColor: "#2f6f4f",
          backgroundColor: "transparent",
          pointRadius: 4,
        },
        {
          label: "max (ueber Wiederholungen)",
          data: data.max,
          borderColor: "rgba(47,111,79,0.25)",
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
        },
        {
          label: "min (ueber Wiederholungen)",
          data: data.min,
          borderColor: "rgba(47,111,79,0.25)",
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      scales: { x: { title: { display: true, text: parameter } } },
    },
  });
}

function renderChart(data) {
  const ctx = document.getElementById("result-chart");
  const upper = data.mean_opinion.map((m, i) => m + data.std_opinion[i]);
  const lower = data.mean_opinion.map((m, i) => m - data.std_opinion[i]);
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.ticks,
      datasets: [
        {
          label: "Mittlere Meinung",
          data: data.mean_opinion,
          borderColor: "#2f6f4f",
          backgroundColor: "transparent",
          pointRadius: 0,
          tension: 0.15,
        },
        {
          label: "+1 Streuung",
          data: upper,
          borderColor: "rgba(47,111,79,0.25)",
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
        },
        {
          label: "-1 Streuung",
          data: lower,
          borderColor: "rgba(47,111,79,0.25)",
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      scales: { x: { title: { display: true, text: "Zeitschritt" } } },
    },
  });
}

// Initialzustand: eine Mechanik und ein Attributbeispiel vorschlagen
addMechanicRow();
addAttributeRow("threshold", { kind: "beta", params: { a: 2, b: 5, min: 0, max: 1 } });

// ==================== Modus-Umschalter (Einfach/Erweitert) ====================
const modeSimpleBtn = document.getElementById("mode-simple-btn");
const modeAdvancedBtn = document.getElementById("mode-advanced-btn");
const simpleModeEl = document.getElementById("simple-mode");
const advancedPanels = document.querySelectorAll(".advanced-only");

function setMode(mode) {
  const isSimple = mode === "simple";
  simpleModeEl.classList.toggle("hidden", !isSimple);
  advancedPanels.forEach((el) => el.classList.toggle("hidden", isSimple));
  modeSimpleBtn.classList.toggle("active", isSimple);
  modeAdvancedBtn.classList.toggle("active", !isSimple);
}

modeSimpleBtn.addEventListener("click", () => setMode("simple"));
modeAdvancedBtn.addEventListener("click", () => setMode("advanced"));

// ==================== Einfacher Modus (gefuehrter Wizard) ====================
// Jeder Typ baut auf einem echten Beispielszenario auf (siehe scenarios/*.json) -
// die zugrundeliegenden realen Datenquellen (Destatis, Eurobarometer, Rogers,
// Nielsen) bleiben erhalten, nur die Bedienung ist reduziert auf EINEN Regler
// plus Gruppengroesse/Dauer statt des vollen Formulars.
const WIZARD_TYPES = {
  meinung: {
    label: "Meinungsbildung",
    description: "Wie sich Meinungen in einer Gruppe entwickeln - bilden sich Lager, oder einigt man sich?",
    exampleFile: "beispiel_bounded_confidence.json",
    sliderLabel: "Wie offen sind Menschen für andere Meinungen?",
    sliderMin: 0.1,
    sliderMax: 1.0,
    sliderStep: 0.05,
    sliderDefault: 0.3,
    sliderLowText: "sehr verschlossen",
    sliderHighText: "sehr offen",
    applySlider: (config, value) => {
      config.mechanics[0].params.epsilon = value;
    },
    supportsEvent: true,
    eventLabel: "Ein aufrüttelndes Ereignis einbauen (z.B. eine virale Nachricht)?",
    addEvent: (config, tick) => {
      config.events = [{ tick, type: "narrow_confidence", params: { factor: 0.3, duration: 15 } }];
    },
    summarySentence: (s) =>
      `Du simulierst, wie sich Meinungen zum Klimawandel bei ${s.size} Personen entwickeln. ` +
      `Sie orientieren sich ${s.sliderDesc} an Menschen mit ähnlicher Meinung. ` +
      `Beobachtet wird über ${s.duration} Zeitschritte.` +
      (s.eventOn ? ` Bei Schritt ${s.eventTick} kommt ein aufrüttelndes Ereignis dazu.` : ""),
    interpret: (data) => {
      const std = data.std_opinion[data.std_opinion.length - 1];
      const mean = data.mean_opinion[data.mean_opinion.length - 1];
      let sentence;
      if (std < 0.15) sentence = "Die Gruppe einigt sich am Ende weitgehend auf eine gemeinsame Meinung.";
      else if (std > 0.4) sentence = "Die Gruppe bleibt am Ende deutlich gespalten - es bildet sich keine gemeinsame Meinung.";
      else sentence = "Es bildet sich eine Tendenz, aber ein Teil der Gruppe bleibt anderer Meinung.";
      if (mean > 0.2) sentence += " Die Mehrheit tendiert dazu, das Thema ernst zu nehmen.";
      else if (mean < -0.2) sentence += " Die Mehrheit tendiert dazu, das Thema nicht ernst zu nehmen.";
      return sentence;
    },
  },
  verhalten: {
    label: "Verhaltensverbreitung",
    description: "Wie sich ein neues Verhalten (z.B. ein Trend) in einer Gruppe ausbreitet.",
    exampleFile: "beispiel_schwellenwert.json",
    sliderLabel: "Wie gut ist die Gruppe vernetzt?",
    sliderMin: 4,
    sliderMax: 25,
    sliderStep: 1,
    sliderDefault: 15,
    sliderLowText: "locker vernetzt",
    sliderHighText: "eng vernetzt",
    applySlider: (config, value) => {
      config.network.params.k = value;
    },
    supportsEvent: false,
    summarySentence: (s) =>
      `Du simulierst, wie sich ein neues Verhalten bei ${s.size} Personen ausbreitet. ` +
      `Die Gruppe ist ${s.sliderDesc}. Beobachtet wird über ${s.duration} Zeitschritte.`,
    interpret: (data) => {
      const share = data.mean_opinion[data.mean_opinion.length - 1];
      const pct = Math.round(share * 100);
      let sentence = `Am Ende haben ${pct}% der Gruppe das neue Verhalten übernommen.`;
      if (share < 0.15) sentence += " Die Ausbreitung ist weitgehend ins Stocken geraten.";
      else if (share > 0.8) sentence += " Fast alle haben mitgezogen - ein klarer Trend.";
      else sentence += " Ein Teil der Gruppe ist dabei, der Rest (noch) nicht.";
      return sentence;
    },
  },
  information: {
    label: "Informationsverbreitung",
    description: "Wie glaubwürdig verschiedene Personen eine Botschaft weitertragen.",
    exampleFile: "beispiel_degroot.json",
    sliderLabel: "Wie stark bleiben Menschen bei ihrer eigenen Meinung?",
    sliderMin: 0.1,
    sliderMax: 0.9,
    sliderStep: 0.05,
    sliderDefault: 0.6,
    sliderLowText: "leicht beeinflussbar",
    sliderHighText: "sehr eigenständig",
    applySlider: (config, value) => {
      config.mechanics[0].params.self_weight = value;
    },
    supportsEvent: true,
    eventLabel: "Eine gezielte Falschinformation einstreuen?",
    addEvent: (config, tick) => {
      config.events = [{ tick, type: "shift_opinion", params: { delta: 0.4, fraction: 0.05 } }];
    },
    summarySentence: (s) =>
      `Du simulierst, wie glaubwürdig ${s.size} Personen eine Nachricht weitertragen. ` +
      `Sie sind dabei ${s.sliderDesc}. Beobachtet wird über ${s.duration} Zeitschritte.` +
      (s.eventOn ? ` Bei Schritt ${s.eventTick} wird gezielt Falschinformation gestreut.` : ""),
    interpret: (data) => {
      const std = data.std_opinion[data.std_opinion.length - 1];
      const mean = data.mean_opinion[data.mean_opinion.length - 1];
      if (std < 0.05) {
        let sentence = "Am Ende teilt die Gruppe eine gemeinsame Einschätzung der Nachricht:";
        if (mean > 0.6) sentence += " Sie hält sie für wahr.";
        else if (mean < 0.4) sentence += " Sie hält sie für falsch.";
        else sentence += " Sie ist sich einig, dass die Wahrheit unklar bleibt.";
        return sentence;
      }
      let sentence = "Die Einschätzungen bleiben unterschiedlich - keine einheitliche Meinung zur Nachricht.";
      if (mean > 0.6) sentence += " Tendenziell hält die Mehrheit sie eher für wahr.";
      else if (mean < 0.4) sentence += " Tendenziell hält die Mehrheit sie eher für falsch.";
      else sentence += " Die Gruppe ist gespalten, ob sie stimmt.";
      return sentence;
    },
  },
};

const SIZE_OPTIONS = [
  { label: "Klein", value: 100 },
  { label: "Mittel", value: 300 },
  { label: "Groß", value: 800 },
];
const DURATION_OPTIONS = [
  { label: "Kurz", value: 20 },
  { label: "Mittel", value: 50 },
  { label: "Lang", value: 100 },
];

let wizardTypeKey = null;
let wizardSize = SIZE_OPTIONS[1].value;
let wizardDuration = DURATION_OPTIONS[1].value;
let wizardLastConfig = null;
let wizardLastResult = null;
let wizardChart = null;

function getExampleConfig(filename) {
  const entry = loadedExamples.find((ex) => ex.file === filename);
  if (!entry) return null;
  const config = JSON.parse(entry.config);
  // scenarios/*.json duerfen 'mechanics' als einzelnes Objekt ODER Liste haben
  // (config.py akzeptiert beides) - der Wizard erwartet immer eine Liste.
  if (!Array.isArray(config.mechanics)) config.mechanics = [config.mechanics];
  return config;
}

function showWizardStep(stepEl) {
  document.querySelectorAll("#simple-mode .wizard-step").forEach((el) => el.classList.add("hidden"));
  stepEl.classList.remove("hidden");
  const stepNumber = {
    "wizard-step-1": 1,
    "wizard-custom-setup": 1,
    "wizard-step-2": 2,
    "wizard-step-3": 3,
    "wizard-result": 3,
  }[stepEl.id];
  document.querySelectorAll(".wizard-dot").forEach((dot) => {
    const n = parseInt(dot.dataset.step, 10);
    dot.classList.toggle("active", n === stepNumber);
    dot.classList.toggle("done", n < stepNumber);
  });
}

function renderWizardCards() {
  const container = document.getElementById("wizard-type-cards");
  container.innerHTML = "";
  Object.entries(WIZARD_TYPES).forEach(([key, type]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "wizard-card";
    btn.innerHTML = `<strong>${type.label}</strong><span>${type.description}</span>`;
    btn.addEventListener("click", () => {
      wizardIsCustom = false;
      wizardTypeKey = key;
      renderWizardStep2();
      showWizardStep(document.getElementById("wizard-step-2"));
    });
    container.appendChild(btn);
  });

  const customBtn = document.createElement("button");
  customBtn.type = "button";
  customBtn.className = "wizard-card";
  customBtn.innerHTML =
    "<strong>Eigenes Szenario</strong><span>Eigenes Thema mit passenden echten Daten oder einer eigenen Schätzung als Ausgangswert.</span>";
  customBtn.addEventListener("click", () => {
    wizardIsCustom = true;
    renderWizardCustomSetup();
    showWizardStep(document.getElementById("wizard-custom-setup"));
  });
  container.appendChild(customBtn);
}

// ---- "Eigenes Szenario": Thema + zugrundeliegende Kategorie + Datenquelle ----
const CUSTOM_APPLIES_TO = { meinung: "opinion_continuous", verhalten: "initial_adoption", information: null };
const CUSTOM_ESTIMATE_LABEL = {
  meinung: "Wie viele finden das Thema anfangs sehr wichtig?",
  verhalten: "Wie viele haben es anfangs schon übernommen?",
  information: "Wie viele halten es anfangs für glaubwürdig?",
};

let wizardIsCustom = false;
let wizardCustomSource = null; // ausgewaehlter Katalogeintrag ODER null (= eigene Schaetzung)

function renderWizardCustomSetup() {
  const container = document.getElementById("wizard-custom-kind-cards");
  container.innerHTML = "";
  ["meinung", "verhalten", "information"].forEach((key) => {
    const type = WIZARD_TYPES[key];
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "wizard-card";
    btn.innerHTML = `<strong>${type.label}</strong><span>${type.description}</span>`;
    btn.addEventListener("click", async () => {
      Array.from(container.children).forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      wizardTypeKey = key;
      document.getElementById("wizard-custom-next").disabled = false;
      await renderCustomSourceGroup(key);
    });
    container.appendChild(btn);
  });
}

async function renderCustomSourceGroup(key) {
  const group = document.getElementById("wizard-custom-source-group");
  const appliesTo = CUSTOM_APPLIES_TO[key];
  document.getElementById("wizard-custom-estimate-label").textContent = CUSTOM_ESTIMATE_LABEL[key];
  wizardCustomSource = null;

  let catalog = [];
  if (appliesTo) {
    try {
      const resp = await fetch(`/api/data-sources?applies_to=${encodeURIComponent(appliesTo)}`);
      catalog = await resp.json();
    } catch {
      catalog = [];
    }
  }

  const options = [...catalog.map((entry) => ({ label: entry.label, value: entry })), { label: "Eigene Schätzung", value: null }];
  renderChoiceRow(document.getElementById("wizard-custom-source-choice"), options, null, (value) => {
    wizardCustomSource = value;
    document.getElementById("wizard-custom-source-citation").textContent = value ? value.citation : "";
    document.getElementById("wizard-custom-estimate-group").classList.toggle("hidden", !!value);
  });
  // Erste Option (falls vorhanden) macht die Radio-Buttons vergleichbar, Auswahl per Klick noetig -
  // Default ist "Eigene Schaetzung", da eine reale Quelle nur passt, wenn sie zum eigenen Thema passt.
  document.getElementById("wizard-custom-estimate-group").classList.remove("hidden");
  document.getElementById("wizard-custom-source-citation").textContent = "";
  group.classList.remove("hidden");
}

document.getElementById("wizard-custom-estimate").addEventListener("input", (e) => {
  document.getElementById("wizard-custom-estimate-value").textContent = `${e.target.value}%`;
});

document.getElementById("wizard-custom-back").addEventListener("click", () => {
  showWizardStep(document.getElementById("wizard-step-1"));
});

document.getElementById("wizard-custom-next").addEventListener("click", () => {
  renderWizardStep2();
  showWizardStep(document.getElementById("wizard-step-2"));
});

function customInitialStateDistribution() {
  if (wizardCustomSource) {
    return { ...wizardCustomSource.distribution, source: wizardCustomSource.citation };
  }
  const pct = parseInt(document.getElementById("wizard-custom-estimate").value, 10);
  const label = `Eigene Schätzung: ${pct}%`;
  if (wizardTypeKey === "verhalten") {
    return { kind: "choice", params: { options: [0.0, 1.0], weights: [1 - pct / 100, pct / 100] }, source: label };
  }
  if (wizardTypeKey === "information") {
    return { kind: "normal", params: { mean: pct / 100, std: 0.25, min: 0.0, max: 1.0 }, source: label };
  }
  return { kind: "normal", params: { mean: (pct / 100) * 2 - 1, std: 0.4, min: -1.0, max: 1.0 }, source: label };
}

function renderChoiceRow(container, options, current, onPick) {
  container.innerHTML = "";
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = opt.label;
    btn.className = opt.value === current ? "active" : "";
    btn.addEventListener("click", () => {
      onPick(opt.value);
      Array.from(container.children).forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
    });
    container.appendChild(btn);
  });
}

function renderWizardStep2() {
  const type = WIZARD_TYPES[wizardTypeKey];

  renderChoiceRow(document.getElementById("wizard-size-choice"), SIZE_OPTIONS, wizardSize, (v) => (wizardSize = v));
  renderChoiceRow(document.getElementById("wizard-duration-choice"), DURATION_OPTIONS, wizardDuration, (v) => (wizardDuration = v));

  document.getElementById("wizard-slider-label").textContent = type.sliderLabel;
  document.getElementById("wizard-slider-low").textContent = type.sliderLowText;
  document.getElementById("wizard-slider-high").textContent = type.sliderHighText;
  const slider = document.getElementById("wizard-slider");
  slider.min = type.sliderMin;
  slider.max = type.sliderMax;
  slider.step = type.sliderStep;
  slider.value = type.sliderDefault;

  const eventGroup = document.getElementById("wizard-event-group");
  eventGroup.classList.toggle("hidden", !type.supportsEvent);
  document.getElementById("wizard-event-label").textContent = type.eventLabel || "";
  const eventToggle = document.getElementById("wizard-event-toggle");
  eventToggle.checked = false;
  document.getElementById("wizard-event-tick-group").classList.add("hidden");
  document.getElementById("wizard-event-tick").value = Math.round(wizardDuration / 3);
}

document.getElementById("wizard-event-toggle").addEventListener("change", (e) => {
  document.getElementById("wizard-event-tick-group").classList.toggle("hidden", !e.target.checked);
});

document.getElementById("wizard-back-1").addEventListener("click", () => {
  showWizardStep(document.getElementById(wizardIsCustom ? "wizard-custom-setup" : "wizard-step-1"));
});

document.getElementById("wizard-next-2").addEventListener("click", () => {
  renderWizardStep3();
  showWizardStep(document.getElementById("wizard-step-3"));
});

document.getElementById("wizard-back-2").addEventListener("click", () => showWizardStep(document.getElementById("wizard-step-2")));

function buildWizardConfig() {
  const type = WIZARD_TYPES[wizardTypeKey];
  const base = getExampleConfig(type.exampleFile);
  if (!base) return null;

  base.population.size = wizardSize;
  base.time.steps = wizardDuration;

  const sliderValue = parseFloat(document.getElementById("wizard-slider").value);
  type.applySlider(base, sliderValue);

  const eventOn = type.supportsEvent && document.getElementById("wizard-event-toggle").checked;
  if (eventOn) {
    const tick = parseInt(document.getElementById("wizard-event-tick").value, 10);
    type.addEvent(base, tick);
  } else {
    base.events = [];
  }

  if (wizardIsCustom) {
    base.initial_state.opinion = customInitialStateDistribution();
    const topic = document.getElementById("wizard-custom-topic").value.trim();
    base.name = topic ? `Eigenes Szenario: ${topic}` : "Eigenes Szenario";
  }

  return base;
}

function renderWizardStep3() {
  const type = WIZARD_TYPES[wizardTypeKey];
  const sliderValue = parseFloat(document.getElementById("wizard-slider").value);
  const midpoint = (type.sliderMin + type.sliderMax) / 2;
  const sliderDesc = sliderValue < midpoint ? type.sliderLowText : type.sliderHighText;
  const eventOn = type.supportsEvent && document.getElementById("wizard-event-toggle").checked;
  const eventTick = document.getElementById("wizard-event-tick").value;

  if (wizardIsCustom) {
    const topic = document.getElementById("wizard-custom-topic").value.trim() || "dein Thema";
    const sourceNote = wizardCustomSource
      ? `Ausgangswerte basieren auf: ${wizardCustomSource.label}.`
      : `Ausgangswerte: eigene Schätzung (${document.getElementById("wizard-custom-estimate").value}%).`;
    document.getElementById("wizard-summary").textContent =
      `Du simulierst "${topic}" (${type.label.toLowerCase()}) bei ${wizardSize} Personen. ` +
      `Sie sind dabei ${sliderDesc}. Beobachtet wird über ${wizardDuration} Zeitschritte. ${sourceNote}` +
      (eventOn ? ` Bei Schritt ${eventTick} kommt ein Ereignis dazu.` : "");
    return;
  }

  document.getElementById("wizard-summary").textContent = type.summarySentence({
    size: wizardSize,
    duration: wizardDuration,
    sliderDesc,
    eventOn,
    eventTick,
  });
}

document.getElementById("wizard-run").addEventListener("click", async () => {
  const wizardError = document.getElementById("wizard-error");
  wizardError.classList.add("hidden");

  const config = buildWizardConfig();
  if (!config) {
    wizardError.textContent = "Beispiel-Konfiguration noch nicht geladen - bitte kurz warten und erneut versuchen.";
    wizardError.classList.remove("hidden");
    return;
  }
  wizardLastConfig = config;

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await response.json();
    if (!response.ok) {
      wizardError.textContent = data.error || "Unbekannter Fehler";
      wizardError.classList.remove("hidden");
      return;
    }
    wizardLastResult = data;
    document.getElementById("wizard-interpretation").textContent = WIZARD_TYPES[wizardTypeKey].interpret(data);
    renderWizardChart(data);
    showWizardStep(document.getElementById("wizard-result"));
  } catch (err) {
    wizardError.textContent = `Verbindung zum Server fehlgeschlagen: ${err.message}`;
    wizardError.classList.remove("hidden");
  }
});

function renderWizardChart(data) {
  const ctx = document.getElementById("wizard-chart");
  if (wizardChart) wizardChart.destroy();
  wizardChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.ticks,
      datasets: [
        {
          label: "Mittlerer Wert",
          data: data.mean_opinion,
          borderColor: "#2f6f4f",
          backgroundColor: "transparent",
          pointRadius: 0,
          tension: 0.15,
        },
      ],
    },
    options: { responsive: true, scales: { x: { title: { display: true, text: "Zeitschritt" } } } },
  });
}

document.getElementById("wizard-restart").addEventListener("click", () => {
  wizardTypeKey = null;
  wizardIsCustom = false;
  wizardCustomSource = null;
  document.getElementById("wizard-custom-topic").value = "";
  document.getElementById("wizard-custom-next").disabled = true;
  document.getElementById("wizard-custom-source-group").classList.add("hidden");
  showWizardStep(document.getElementById("wizard-step-1"));
});

document.getElementById("wizard-open-advanced").addEventListener("click", () => {
  if (wizardLastConfig) loadConfigIntoForm(wizardLastConfig);
  setMode("advanced");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

renderWizardCards();
