const history = [];

const $ = (id) => document.getElementById(id);

function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

function setPill(el, text, kind) {
  el.textContent = text;
  el.classList.remove("ok", "warn", "muted");
  if (kind) el.classList.add(kind);
}

async function refreshHealth() {
  try {
    const health = await fetchJSON("/health");
    setPill($("healthPill"), health.ok ? "API online" : "API degraded", health.ok ? "ok" : "warn");
    setPill(
      $("tracePill"),
      health.tracing_enabled ? "Langfuse on" : "Langfuse off",
      health.tracing_enabled ? "ok" : "warn",
    );
    updateIncidentButtons(health.incidents || {});
  } catch (err) {
    setPill($("healthPill"), "API offline", "warn");
    setPill($("tracePill"), "Tracing ?", "muted");
  }
}

function updateIncidentButtons(incidents) {
  document.querySelectorAll("[data-incident]").forEach((btn) => {
    const name = btn.dataset.incident;
    const on = Boolean(incidents[name]);
    btn.textContent = on ? "Disable" : "Enable";
    btn.classList.toggle("active", on);
    btn.dataset.active = on ? "1" : "0";
  });
}

async function refreshMetrics() {
  try {
    const m = await fetchJSON("/metrics");
    $("mLatency").textContent = fmt(m.latency_p95, 0);
    $("mLatencyDetail").textContent = `P50 ${fmt(m.latency_p50, 0)} · P95 ${fmt(m.latency_p95, 0)} · P99 ${fmt(m.latency_p99, 0)}`;
    const bar = Math.min(100, (m.latency_p95 / 3000) * 100);
    $("mLatencyBar").style.width = `${bar}%`;

    $("heroP95").textContent = `${fmt(m.latency_p95, 0)} ms`;
    $("heroMeta").textContent =
      m.traffic > 0
        ? `${fmt(m.traffic)} requests · quality ${fmt(m.quality_avg, 2)}`
        : "Waiting for traffic";

    $("mTraffic").textContent = fmt(m.traffic);
    const errCount = Object.values(m.error_breakdown || {}).reduce((a, b) => a + b, 0);
    $("mErrors").textContent = fmt(errCount);
    $("mErrorsDetail").textContent =
      errCount === 0
        ? "No errors"
        : Object.entries(m.error_breakdown)
            .map(([k, v]) => `${k}:${v}`)
            .join(" · ");

    $("mCost").textContent = `$${fmt(m.total_cost_usd, 4)}`;
    $("mCostDetail").textContent = `avg $${fmt(m.avg_cost_usd, 4)}`;
    $("mTokens").textContent = fmt((m.tokens_in_total || 0) + (m.tokens_out_total || 0));
    $("mTokensDetail").textContent = `in ${fmt(m.tokens_in_total)} · out ${fmt(m.tokens_out_total)}`;
    $("mQuality").textContent = fmt(m.quality_avg, 2);
  } catch (_) {
    /* ignore transient poll errors */
  }
}

async function refreshLogs() {
  try {
    const data = await fetchJSON("/demo/recent-logs?limit=25");
    const lines = (data.records || []).map((row) => {
      const cid = row.correlation_id || "-";
      const preview = row.payload?.message_preview || row.payload?.answer_preview || "";
      const latency = row.latency_ms != null ? `${row.latency_ms}ms` : "";
      return [
        row.ts || "",
        row.level || "",
        row.event || "",
        cid,
        row.feature || "",
        latency,
        preview,
      ]
        .filter(Boolean)
        .join(" | ");
    });
    $("logTail").textContent = lines.length ? lines.join("\n") : "No log records yet. Send a chat request.";
  } catch (err) {
    $("logTail").textContent = `Could not load logs: ${err.message}`;
  }
}

function renderHistory() {
  const body = $("historyBody");
  if (!history.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty">No requests yet.</td></tr>`;
    return;
  }
  body.innerHTML = history
    .slice()
    .reverse()
    .map(
      (item) => `<tr>
        <td>${item.time}</td>
        <td><code>${item.correlation_id}</code></td>
        <td>${item.feature}</td>
        <td>${item.latency_ms} ms</td>
        <td>${fmt(item.quality_score, 2)}</td>
        <td>$${fmt(item.cost_usd, 4)}</td>
      </tr>`,
    )
    .join("");
}

async function sendChat(event) {
  event.preventDefault();
  const btn = $("sendBtn");
  btn.disabled = true;
  btn.textContent = "Sending…";
  const payload = {
    user_id: $("userId").value.trim() || "demo-user-01",
    session_id: $("sessionId").value.trim() || "demo-session-01",
    feature: $("feature").value,
    message: $("message").value.trim(),
  };
  if (!payload.message) {
    btn.disabled = false;
    btn.textContent = "Send request";
    return;
  }
  try {
    const data = await fetchJSON("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    $("chatResponse").hidden = false;
    $("outCid").textContent = data.correlation_id;
    $("outLatency").textContent = `${data.latency_ms} ms`;
    $("outTokens").textContent = `${data.tokens_in} / ${data.tokens_out}`;
    $("outCost").textContent = `$${fmt(data.cost_usd, 4)}`;
    $("outQuality").textContent = fmt(data.quality_score, 2);
    $("outAnswer").textContent = data.answer;
    history.push({
      time: new Date().toLocaleTimeString(),
      feature: payload.feature,
      ...data,
    });
    renderHistory();
    await Promise.all([refreshMetrics(), refreshLogs(), refreshHealth()]);
  } catch (err) {
    $("chatResponse").hidden = false;
    $("outAnswer").textContent = `Request failed: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Send request";
  }
}

async function toggleIncident(name, currentlyActive) {
  const path = currentlyActive ? "disable" : "enable";
  const data = await fetchJSON(`/incidents/${name}/${path}`, { method: "POST" });
  updateIncidentButtons(data.incidents || {});
}

function wireEvents() {
  $("chatForm").addEventListener("submit", sendChat);
  $("samplePiiBtn").addEventListener("click", () => {
    $("message").value =
      "What is your refund policy? Contact me at student@vinuni.edu.vn or 0901234567. Card 4111 1111 1111 1111.";
    $("feature").value = "refund";
  });
  document.querySelectorAll("[data-incident]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await toggleIncident(btn.dataset.incident, btn.dataset.active === "1");
      } catch (err) {
        alert(`Incident toggle failed: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

async function boot() {
  wireEvents();
  await Promise.all([refreshHealth(), refreshMetrics(), refreshLogs()]);
  setInterval(() => {
    refreshHealth();
    refreshMetrics();
    refreshLogs();
  }, 5000);
}

boot();
