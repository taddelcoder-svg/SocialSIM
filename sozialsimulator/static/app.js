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

// ---- Netzwerk ----
const networkTypeSelect = document.getElementById("network-type");
const networkParamsEl = document.getElementById("network-params");
function refreshNetworkFields(values = {}) {
  renderFields(networkParamsEl, NETWORK_FIELDS[networkTypeSelect.value], "net", values);
}
networkTypeSelect.addEventListener("change", () => refreshNetworkFields());
refreshNetworkFields();

// ---- Ausgangszustand: ein oder mehrere Meinungsthemen ----
// Ein Thema = ein Eintrag in initial_state (siehe config.py Distribution). Mehrere
// Themen ermoeglichen mehrdimensionale Meinungen; ein Thema kann optional mit einem
// anderen "correlated_with" sein (eine Ebene, siehe model.py._sample_initial_state).
const topicList = document.getElementById("topic-list");

function currentTopicNames() {
  return [...topicList.querySelectorAll(".topic-row")]
    .map((row) => row.querySelector(".topic-name").value.trim())
    .filter(Boolean);
}

function refreshTopicCorrelationOptions() {
  const names = currentTopicNames();
  topicList.querySelectorAll(".topic-row").forEach((row) => {
    const selfName = row.querySelector(".topic-name").value.trim();
    const target = row.querySelector(".topic-corr-target");
    const desired = row.dataset.corrTarget || target.value;
    const others = names.filter((n) => n !== selfName);
    target.innerHTML = others.map((n) => `<option value="${n}">${n}</option>`).join("");
    if (others.includes(desired)) {
      target.value = desired;
      delete row.dataset.corrTarget;
    }
  });
}

function addTopicRow(name = "opinion", dist = { kind: "uniform", params: { min: -1, max: 1 } }) {
  const rowId = `topic-${rowCounter++}`;
  const row = document.createElement("div");
  row.className = "dynamic-row topic-row";
  row.dataset.corrTarget = dist.correlated_with ? dist.correlated_with.topic : "";
  row.innerHTML = `
    <button type="button" class="remove-row" title="entfernen">&times;</button>
    <div class="field-group">
      <label>Thema (Name)</label>
      <input type="text" class="topic-name" value="${name}" placeholder="z.B. klima, energiepolitik" />
    </div>
    <div class="field-group">
      <label>Verteilung</label>
      <select class="topic-kind">
        <option value="uniform">Gleichverteilt (uniform)</option>
        <option value="normal">Normalverteilt (normal)</option>
        <option value="beta">Beta</option>
        <option value="choice">Diskret (choice)</option>
        <option value="constant">Konstant</option>
        <option value="histogram">Histogramm (reale Bins)</option>
      </select>
    </div>
    <div class="row-fields topic-params"></div>
    <div class="field-group">
      <label>Quelle (optional, z.B. "WVS 2022")</label>
      <input type="text" class="topic-source" placeholder="woher stammt dieser Ausgangswert?" />
    </div>
    <div class="field-group topic-corr-group">
      <label><input type="checkbox" class="topic-corr-toggle" /> mit einem anderen Thema korreliert</label>
      <div class="row-fields topic-corr-fields hidden">
        <select class="topic-corr-target"></select>
        <input type="number" class="topic-corr-strength" min="0" max="1" step="0.05" placeholder="Staerke (0-1)" />
      </div>
    </div>
  `;
  topicList.appendChild(row);

  const nameInput = row.querySelector(".topic-name");
  const kindSelect = row.querySelector(".topic-kind");
  const paramsEl = row.querySelector(".topic-params");
  kindSelect.value = dist.kind;
  renderDistributionParams(paramsEl, kindSelect.value, rowId, dist.params || {});
  row.querySelector(".topic-source").value = dist.source || "";
  kindSelect.addEventListener("change", () => renderDistributionParams(paramsEl, kindSelect.value, rowId));

  const corrToggle = row.querySelector(".topic-corr-toggle");
  const corrFields = row.querySelector(".topic-corr-fields");
  const corrStrength = row.querySelector(".topic-corr-strength");
  corrStrength.value = dist.correlated_with ? dist.correlated_with.strength ?? 0.5 : 0.5;
  if (dist.correlated_with) {
    corrToggle.checked = true;
    corrFields.classList.remove("hidden");
  }
  corrToggle.addEventListener("change", () => corrFields.classList.toggle("hidden", !corrToggle.checked));

  nameInput.addEventListener("input", () => {
    refreshTopicCorrelationOptions();
    refreshMechanicTopicOptions();
  });
  row.querySelector(".remove-row").addEventListener("click", () => {
    if (topicList.querySelectorAll(".topic-row").length > 1) {
      row.remove();
      refreshTopicCorrelationOptions();
      refreshMechanicTopicOptions();
    }
  });

  refreshTopicCorrelationOptions();
  refreshMechanicTopicOptions();
}

document.getElementById("add-topic").addEventListener("click", () => addTopicRow(`thema${topicList.querySelectorAll(".topic-row").length + 1}`));

function readTopics() {
  const out = {};
  topicList.querySelectorAll(".topic-row").forEach((row) => {
    const name = row.querySelector(".topic-name").value.trim();
    if (!name) return;
    const kindSelect = row.querySelector(".topic-kind");
    const paramsEl = row.querySelector(".topic-params");
    const dist = { kind: kindSelect.value, params: readDistributionParams(paramsEl, kindSelect.value) };
    const source = row.querySelector(".topic-source").value.trim();
    if (source) dist.source = source;
    const corrToggle = row.querySelector(".topic-corr-toggle");
    if (corrToggle.checked) {
      const target = row.querySelector(".topic-corr-target").value;
      const strength = parseFloat(row.querySelector(".topic-corr-strength").value);
      if (target) dist.correlated_with = { topic: target, strength: isNaN(strength) ? 0.5 : strength };
    }
    out[name] = dist;
  });
  return out;
}

// ---- Mechanik (eine oder mehrere, in Ausfuehrungsreihenfolge) ----
const MECHANIC_LABELS = {
  bounded_confidence: "Bounded Confidence (Hegselmann-Krause)",
  threshold: "Schwellenwertmodell (Granovetter)",
  degroot: "DeGroot-Lernen",
};
const mechanicList = document.getElementById("mechanic-list");

function refreshMechanicTopicOptions() {
  const names = currentTopicNames();
  mechanicList.querySelectorAll(".dynamic-row").forEach((row) => {
    const select = row.querySelector(".mech-topic");
    if (!select) return;
    const desired = row.dataset.topic || select.value;
    select.innerHTML = names.map((n) => `<option value="${n}">${n}</option>`).join("");
    if (names.includes(desired)) {
      select.value = desired;
      delete row.dataset.topic;
    }
  });
}

function addMechanicRow(model = "bounded_confidence", params = {}, topic = "opinion") {
  const rowId = `mech-${rowCounter++}`;
  const row = document.createElement("div");
  row.className = "dynamic-row";
  row.dataset.topic = topic;
  row.innerHTML = `
    <button type="button" class="remove-row" title="entfernen">&times;</button>
    <div class="field-group">
      <label>Modell</label>
      <select class="mech-model">
        ${Object.entries(MECHANIC_LABELS).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
      </select>
    </div>
    <div class="field-group">
      <label>Thema</label>
      <select class="mech-topic"></select>
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
  refreshMechanicTopicOptions();
}

document.getElementById("add-mechanic").addEventListener("click", () => addMechanicRow());

function readMechanics() {
  const out = [];
  mechanicList.querySelectorAll(".dynamic-row").forEach((row) => {
    const modelSelect = row.querySelector(".mech-model");
    const paramsEl = row.querySelector(".mech-params");
    const topicSelect = row.querySelector(".mech-topic");
    out.push({
      model: modelSelect.value,
      topic: topicSelect && topicSelect.value ? topicSelect.value : "opinion",
      params: readFields(paramsEl, MECHANIC_FIELDS[modelSelect.value]),
    });
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
    initial_state: readTopics(),
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

  topicList.innerHTML = "";
  Object.entries(config.initial_state || {}).forEach(([name, dist]) => addTopicRow(name, dist));

  mechanicList.innerHTML = "";
  const mechanics = Array.isArray(config.mechanics) ? config.mechanics : [config.mechanics];
  mechanics.forEach((m) => addMechanicRow(m.model, m.params || {}, m.topic || "opinion"));

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
    const topics = data.topics && data.topics.length ? data.topics : ["opinion"];
    const spreadText = topics
      .map((t) => {
        const std = data[`std_${t}`];
        return std ? `${t}: ${std[0].toFixed(3)} -> ${std[std.length - 1].toFixed(3)}` : null;
      })
      .filter(Boolean)
      .join(" | ");
    resultSummary.textContent =
      `${data.population_size} Agenten, Mechanik "${data.mechanic}", ` +
      `gemittelt ueber ${data.runs} Lauf/Laeufe. Meinungsstreuung (${spreadText}).`;
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

// Eine Farbe pro Thema, damit mehrdimensionale Szenarien optisch unterscheidbar bleiben.
const TOPIC_COLORS = ["#2f6f4f", "#7a3e9d", "#b0563a", "#2a6f8f", "#8f8f2a"];

function renderChart(data) {
  const ctx = document.getElementById("result-chart");
  const topics = data.topics && data.topics.length ? data.topics : ["opinion"];
  const datasets = [];
  topics.forEach((topic, i) => {
    const mean = data[`mean_${topic}`];
    const std = data[`std_${topic}`];
    if (!mean) return;
    const color = TOPIC_COLORS[i % TOPIC_COLORS.length];
    datasets.push({
      label: topics.length > 1 ? `Mittelwert: ${topic}` : "Mittlere Meinung",
      data: mean,
      borderColor: color,
      backgroundColor: "transparent",
      pointRadius: 0,
      tension: 0.15,
    });
    if (std) {
      const upper = mean.map((m, j) => m + std[j]);
      const lower = mean.map((m, j) => m - std[j]);
      datasets.push(
        {
          label: `+1 Streuung${topics.length > 1 ? `: ${topic}` : ""}`,
          data: upper,
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        },
        {
          label: `-1 Streuung${topics.length > 1 ? `: ${topic}` : ""}`,
          data: lower,
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        }
      );
    }
  });
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: { labels: data.ticks, datasets },
    options: {
      responsive: true,
      scales: { x: { title: { display: true, text: "Zeitschritt" } } },
    },
  });
}

// Initialzustand: ein Thema, eine Mechanik und ein Attributbeispiel vorschlagen
addTopicRow();
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

// ==================== Einfacher Modus: EIN Formular, keine Schritte ====================
// Jede Kategorie baut auf einem echten Beispielszenario auf (scenarios/*.json) -
// die realen Datenquellen (Destatis, Eurobarometer, Rogers, Nielsen) bleiben
// erhalten, nur die Bedienung ist auf das Noetigste reduziert: Thema, EINE
// Kategorie, EIN Regler, EIN Prozentwert. Gruppengroesse/Dauer/Ereignis stehen
// mit sinnvollen Standardwerten unter "Weitere Einstellungen (optional)".
const SIM_KINDS = {
  meinung: {
    label: "Wie sich Meinungen entwickeln",
    description: "Bilden sich Lager, oder einigt sich die Gruppe?",
    exampleFile: "beispiel_bounded_confidence.json",
    sliderLabel: "Wie offen sind Menschen für andere Meinungen?",
    sliderMin: 0.1,
    sliderMax: 1.0,
    sliderStep: 0.05,
    sliderDefault: 0.3,
    sliderLowText: "sehr verschlossen",
    sliderHighText: "sehr offen",
    estimateLabel: "Wie viele finden das Thema anfangs sehr wichtig?",
    appliesTo: "opinion_continuous",
    toPercent: (v) => Math.round(((v + 1) / 2) * 100),
    metricLabel: "Anteil, der das Thema ernst nimmt",
    applySlider: (config, value) => {
      config.mechanics[0].params.epsilon = value;
    },
    estimateDistribution: (pct) => ({
      kind: "normal",
      params: { mean: (pct / 100) * 2 - 1, std: 0.4, min: -1.0, max: 1.0 },
      source: `Eigene Schätzung: ${pct}%`,
    }),
    eventLabel: "Ein aufrüttelndes Ereignis einbauen (z.B. eine virale Nachricht)?",
    addEvent: (config, tick) => {
      config.events = [{ tick, type: "narrow_confidence", params: { factor: 0.3, duration: 15 } }];
    },
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
    label: "Wie sich ein Verhalten verbreitet",
    description: "Zieht die Gruppe mit einem neuen Trend mit, oder verpufft er?",
    exampleFile: "beispiel_schwellenwert.json",
    sliderLabel: "Wie gut ist die Gruppe vernetzt?",
    sliderMin: 4,
    sliderMax: 25,
    sliderStep: 1,
    sliderDefault: 15,
    sliderLowText: "locker vernetzt",
    sliderHighText: "eng vernetzt",
    estimateLabel: "Wie viele haben es anfangs schon übernommen?",
    appliesTo: "initial_adoption",
    toPercent: (v) => Math.round(v * 100),
    metricLabel: "Anteil, der das neue Verhalten übernommen hat",
    applySlider: (config, value) => {
      config.network.params.k = value;
    },
    estimateDistribution: (pct) => ({
      kind: "choice",
      params: { options: [0.0, 1.0], weights: [1 - pct / 100, pct / 100] },
      source: `Eigene Schätzung: ${pct}%`,
    }),
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
    label: "Wie glaubwürdig eine Nachricht bleibt",
    description: "Einigt sich die Gruppe, ob etwas stimmt, oder bleiben die Meinungen verschieden?",
    exampleFile: "beispiel_degroot.json",
    sliderLabel: "Wie stark bleiben Menschen bei ihrer eigenen Meinung?",
    sliderMin: 0.1,
    sliderMax: 0.9,
    sliderStep: 0.05,
    sliderDefault: 0.6,
    sliderLowText: "leicht beeinflussbar",
    sliderHighText: "sehr eigenständig",
    estimateLabel: "Wie viele halten die Nachricht anfangs für glaubwürdig?",
    appliesTo: "trust_media",
    toPercent: (v) => Math.round(v * 100),
    metricLabel: "Anteil, der die Nachricht für glaubwürdig hält",
    applySlider: (config, value) => {
      config.mechanics[0].params.self_weight = value;
    },
    estimateDistribution: (pct) => ({
      kind: "normal",
      params: { mean: pct / 100, std: 0.25, min: 0.0, max: 1.0 },
      source: `Eigene Schätzung: ${pct}%`,
    }),
    eventLabel: "Eine gezielte Falschinformation einstreuen?",
    addEvent: (config, tick) => {
      config.events = [{ tick, type: "shift_opinion", params: { delta: 0.4, fraction: 0.05 } }];
    },
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

const SIM_SIZE_OPTIONS = [
  { label: "Klein", value: 100 },
  { label: "Mittel", value: 300 },
  { label: "Groß", value: 800 },
];
const SIM_DURATION_OPTIONS = [
  { label: "Kurz", value: 20 },
  { label: "Mittel", value: 50 },
  { label: "Lang", value: 100 },
];

let simKindKey = "meinung";
let simSize = SIM_SIZE_OPTIONS[1].value;
let simDuration = SIM_DURATION_OPTIONS[1].value;
let simRealDataEntry = null;
let simLastConfig = null;
let simLastData = null;
let simChart = null;
let simSecondTopicName = null;

function simGetExampleConfig(filename) {
  const entry = loadedExamples.find((ex) => ex.file === filename);
  if (!entry) return null;
  const config = JSON.parse(entry.config);
  if (!Array.isArray(config.mechanics)) config.mechanics = [config.mechanics];
  return config;
}

function simRenderChoiceRow(container, options, current, onPick) {
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

function simRenderKindCards() {
  const container = document.getElementById("s-kind-cards");
  container.innerHTML = "";
  Object.entries(SIM_KINDS).forEach(([key, kind]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "wizard-card" + (key === simKindKey ? " active" : "");
    btn.innerHTML = `<strong>${kind.label}</strong><span>${kind.description}</span>`;
    btn.addEventListener("click", () => {
      simKindKey = key;
      Array.from(container.children).forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      simApplyKind();
    });
    container.appendChild(btn);
  });
}

async function simApplyKind() {
  const kind = SIM_KINDS[simKindKey];

  document.getElementById("s-slider-label").textContent = kind.sliderLabel;
  document.getElementById("s-slider-low").textContent = kind.sliderLowText;
  document.getElementById("s-slider-high").textContent = kind.sliderHighText;
  const slider = document.getElementById("s-slider");
  slider.min = kind.sliderMin;
  slider.max = kind.sliderMax;
  slider.step = kind.sliderStep;
  slider.value = kind.sliderDefault;

  document.getElementById("s-estimate-label").textContent = kind.estimateLabel;

  document.getElementById("s-event-group").classList.toggle("hidden", !kind.eventLabel);
  document.getElementById("s-event-label").textContent = kind.eventLabel || "";
  document.getElementById("s-event-toggle").checked = false;
  document.getElementById("s-event-tick-group").classList.add("hidden");
  document.getElementById("s-event-tick").value = Math.round(simDuration / 3);

  simRealDataEntry = null;
  const realDataRow = document.getElementById("s-real-data-row");
  const select = document.getElementById("s-real-data-select");
  const citationEl = document.getElementById("s-real-data-citation");
  select.innerHTML = '<option value="">Eigene Schätzung (Regler oben)</option>';
  citationEl.textContent = "";
  realDataRow.classList.add("hidden");

  if (kind.appliesTo) {
    try {
      const resp = await fetch(`/api/data-sources?applies_to=${encodeURIComponent(kind.appliesTo)}`);
      const catalog = await resp.json();
      if (catalog.length > 0) {
        catalog.forEach((entry, i) => {
          const opt = document.createElement("option");
          opt.value = String(i);
          opt.textContent = entry.label;
          select.appendChild(opt);
        });
        select.onchange = () => {
          const idx = select.value;
          simRealDataEntry = idx === "" ? null : catalog[parseInt(idx, 10)];
          citationEl.textContent = simRealDataEntry ? simRealDataEntry.citation : "";
        };
        realDataRow.classList.remove("hidden");
      }
    } catch {
      // Katalog nicht erreichbar - Formular bleibt mit eigener Schaetzung nutzbar.
    }
  }
}

document.getElementById("s-estimate").addEventListener("input", (e) => {
  document.getElementById("s-estimate-value").textContent = `${e.target.value}%`;
});

document.getElementById("s-event-toggle").addEventListener("change", (e) => {
  document.getElementById("s-event-tick-group").classList.toggle("hidden", !e.target.checked);
});

document.getElementById("s-second-topic-toggle").addEventListener("change", (e) => {
  document.getElementById("s-second-topic-fields").classList.toggle("hidden", !e.target.checked);
});
document.getElementById("s-second-topic-estimate").addEventListener("input", (e) => {
  document.getElementById("s-second-topic-estimate-value").textContent = `${e.target.value}%`;
});
document.getElementById("s-second-topic-corr").addEventListener("input", (e) => {
  document.getElementById("s-second-topic-corr-value").textContent = `${Math.round(e.target.value * 100)}%`;
});

simRenderChoiceRow(document.getElementById("s-size-choice"), SIM_SIZE_OPTIONS, simSize, (v) => (simSize = v));
simRenderChoiceRow(document.getElementById("s-duration-choice"), SIM_DURATION_OPTIONS, simDuration, (v) => (simDuration = v));

function simBuildConfig() {
  const kind = SIM_KINDS[simKindKey];
  const base = simGetExampleConfig(kind.exampleFile);
  if (!base) return null;

  base.population.size = simSize;
  base.time.steps = simDuration;

  const sliderValue = parseFloat(document.getElementById("s-slider").value);
  kind.applySlider(base, sliderValue);

  const eventOn = kind.eventLabel && document.getElementById("s-event-toggle").checked;
  if (eventOn) {
    const tick = parseInt(document.getElementById("s-event-tick").value, 10);
    kind.addEvent(base, tick);
  } else {
    base.events = [];
  }

  if (simRealDataEntry) {
    base.initial_state.opinion = { ...simRealDataEntry.distribution, source: simRealDataEntry.citation };
  } else {
    const pct = parseInt(document.getElementById("s-estimate").value, 10);
    base.initial_state.opinion = kind.estimateDistribution(pct);
  }

  const topic = document.getElementById("s-topic").value.trim();
  base.name = topic ? `${topic} (${kind.label})` : kind.label;

  // Optionales zweites Thema: nutzt dieselbe Verteilungsform/-spanne wie das
  // erste (kind.estimateDistribution), damit beide Themen vergleichbar bleiben,
  // und wird per correlated_with an "opinion" gekoppelt (siehe config.py). Die
  // gleiche Mechanik/Parameter wie fuer Thema 1 wird zusaetzlich auf das zweite
  // Thema angewendet - ein bewusst einfaches Modell, keine eigene Feinsteuerung.
  simSecondTopicName = null;
  if (document.getElementById("s-second-topic-toggle").checked) {
    const secondName = document.getElementById("s-second-topic-name").value.trim() || "thema2";
    if (secondName !== "opinion") {
      const secondPct = parseInt(document.getElementById("s-second-topic-estimate").value, 10);
      const corrStrength = parseFloat(document.getElementById("s-second-topic-corr").value);
      const secondDist = kind.estimateDistribution(secondPct);
      secondDist.source = `Eigene Schätzung: ${secondPct}% (korreliert mit "opinion", Stärke ${corrStrength})`;
      secondDist.correlated_with = { topic: "opinion", strength: corrStrength };
      base.initial_state[secondName] = secondDist;
      base.mechanics.push({ model: base.mechanics[0].model, topic: secondName, params: { ...base.mechanics[0].params } });
      simSecondTopicName = secondName;
    }
  }

  return base;
}

document.getElementById("s-run").addEventListener("click", async () => {
  const errorBox2 = document.getElementById("s-error");
  errorBox2.classList.add("hidden");

  const config = simBuildConfig();
  if (!config) {
    errorBox2.textContent = "Beispiel-Konfiguration noch nicht geladen - bitte kurz warten und erneut versuchen.";
    errorBox2.classList.remove("hidden");
    return;
  }
  simLastConfig = config;

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await response.json();
    if (!response.ok) {
      errorBox2.textContent = data.error || "Unbekannter Fehler";
      errorBox2.classList.remove("hidden");
      return;
    }
    simLastData = data;
    let interpretation = SIM_KINDS[simKindKey].interpret(data);
    if (simSecondTopicName && data[`std_${simSecondTopicName}`]) {
      interpretation += " " + simInterpretSecondTopic(data, simSecondTopicName);
    }
    document.getElementById("s-interpretation").textContent = interpretation;
    simRenderChart(data);
    simRenderProjection();
    document.getElementById("s-result").classList.remove("hidden");
    document.getElementById("s-result").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    errorBox2.textContent = `Verbindung zum Server fehlgeschlagen: ${err.message}`;
    errorBox2.classList.remove("hidden");
  }
});

// Generische, an SIM_KINDS.interpret angelehnte Einschaetzung fuer ein zweites
// (optionales, korreliertes) Thema - bewusst grob (Konvergenz ja/nein), keine
// kind-spezifische Formulierung wie beim ersten Thema.
function simInterpretSecondTopic(data, topicName) {
  const std = data[`std_${topicName}`];
  const mean = data[`mean_${topicName}`];
  const lastStd = std[std.length - 1];
  const lastMean = mean[mean.length - 1];
  let sentence = `Beim zweiten Thema ("${topicName}") `;
  if (lastStd < 0.15) sentence += "einigt sich die Gruppe ebenfalls weitgehend, ";
  else if (lastStd > 0.4) sentence += "bleibt die Gruppe ebenfalls deutlich gespalten, ";
  else sentence += "bildet sich eine Tendenz, aber kein einheitliches Bild, ";
  sentence += `bei einem mittleren Wert von ${lastMean.toFixed(2)}.`;
  return sentence;
}

function simRenderChart(data) {
  const ctx = document.getElementById("s-chart");
  if (simChart) simChart.destroy();
  const topics = simSecondTopicName ? ["opinion", simSecondTopicName] : ["opinion"];
  const datasets = [];
  topics.forEach((topic, i) => {
    const mean = data[`mean_${topic}`];
    if (!mean) return;
    const color = TOPIC_COLORS[i % TOPIC_COLORS.length];
    datasets.push({
      label: topics.length > 1 ? `Mittelwert: ${topic}` : "Mittlerer Wert",
      data: mean,
      borderColor: color,
      backgroundColor: "transparent",
      pointRadius: 0,
      tension: 0.15,
    });
    // Bandbreite ueber die Wiederholungslaeufe (mean_<topic>_min/max) gibt es
    // serverseitig bisher nur fuer "opinion" (webapp.py) - fuer das zweite
    // Thema zeigen wir stattdessen die Streuung ZWISCHEN Agenten (std_<topic>).
    if (topic === "opinion" && data.mean_opinion_max) {
      datasets.push(
        {
          label: "max. Wiederholungslauf",
          data: data.mean_opinion_max,
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        },
        {
          label: "min. Wiederholungslauf",
          data: data.mean_opinion_min,
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        }
      );
    } else if (data[`std_${topic}`]) {
      const std = data[`std_${topic}`];
      datasets.push(
        {
          label: `+1 Streuung: ${topic}`,
          data: mean.map((m, j) => m + std[j]),
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        },
        {
          label: `-1 Streuung: ${topic}`,
          data: mean.map((m, j) => m - std[j]),
          borderColor: color,
          backgroundColor: "transparent",
          pointRadius: 0,
          borderDash: [4, 4],
          borderWidth: 1,
        }
      );
    }
  });
  simChart = new Chart(ctx, {
    type: "line",
    data: { labels: data.ticks, datasets },
    options: { responsive: true, scales: { x: { title: { display: true, text: "Zeitschritt" } } } },
  });
}

// ---- Zukunftsprojektion: reale Zeitspanne + Bandbreite aus den Wiederholungslaeufen ----
// Bewusst keine "genaue Vorhersage": das Framework-Dokument (Abschnitt 1) schliesst das
// explizit aus. Stattdessen ein klar ausgewiesener plausibler Bereich aus dem, was die
// Simulation selbst an Streuung zwischen ihren Laeufen zeigt - mit Caveat im Text.
function simRenderProjection() {
  if (!simLastData) return;
  const kind = SIM_KINDS[simKindKey];
  const lastIdx = simLastData.ticks.length - 1;
  const steps = simLastData.ticks[lastIdx];

  const meanPct = kind.toPercent(simLastData.mean_opinion[lastIdx]);
  const minPct = kind.toPercent(simLastData.mean_opinion_min[lastIdx]);
  const maxPct = kind.toPercent(simLastData.mean_opinion_max[lastIdx]);

  const tickCount = parseFloat(document.getElementById("s-tick-count").value) || 1;
  const tickUnit = document.getElementById("s-tick-unit").value;
  const totalRealSpan = Math.round(steps * tickCount * 10) / 10;

  const rangeText =
    minPct === maxPct
      ? `bei etwa ${meanPct}%`
      : `zwischen ${Math.min(minPct, maxPct)}% und ${Math.max(minPct, maxPct)}% (Mittel: ${meanPct}%)`;

  document.getElementById("s-projection").textContent =
    `Wenn sich diese Dynamik unverändert über ${totalRealSpan} ${tickUnit} fortsetzt, liegt der ${kind.metricLabel} ` +
    `laut den ${simLastData.runs} Wiederholungsläufen dieser Simulation plausibel ${rangeText}. ` +
    `Das ist eine modellbasierte Spekulation, keine Vorhersage: reale Ereignisse, neue Informationen ` +
    `oder geänderte Rahmenbedingungen können den tatsächlichen Verlauf jederzeit ändern.`;
}

document.getElementById("s-tick-count").addEventListener("input", simRenderProjection);
document.getElementById("s-tick-unit").addEventListener("change", simRenderProjection);

document.getElementById("s-open-advanced").addEventListener("click", () => {
  if (simLastConfig) loadConfigIntoForm(simLastConfig);
  setMode("advanced");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

simRenderKindCards();
simApplyKind();

