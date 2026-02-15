(function () {
  const body = document.body;
  const tenantId = body.dataset.tenantId || new URLSearchParams(window.location.search).get("tenant_id") || "";

  function qs(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function showToast(message) {
    const stack = qs("toast-stack");
    if (!stack) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    stack.appendChild(toast);
    setTimeout(() => toast.classList.add("visible"), 10);
    setTimeout(() => {
      toast.classList.remove("visible");
      setTimeout(() => toast.remove(), 180);
    }, 2200);
  }

  const toastMap = {
    "client-created": "Client created.",
    "project-created": "Project created.",
    "financials-updated": "Client financials updated.",
    "campaign-created": "Campaign saved to Marketing.",
  };

  const params = new URLSearchParams(window.location.search);
  const themeToggle = qs("theme-toggle");
  const storedTheme = localStorage.getItem("theme_mode");
  if (storedTheme === "light") {
    body.classList.add("theme-light");
  }

  const easyToggle = qs("easy-toggle");
  const storedEasyMode = localStorage.getItem("easy_mode");
  if (storedEasyMode === "on") {
    body.classList.add("easy-mode");
  }
  if (easyToggle) {
    easyToggle.textContent = body.classList.contains("easy-mode") ? "Easy: On" : "Easy";
    easyToggle.addEventListener("click", () => {
      body.classList.toggle("easy-mode");
      const isOn = body.classList.contains("easy-mode");
      localStorage.setItem("easy_mode", isOn ? "on" : "off");
      easyToggle.textContent = isOn ? "Easy: On" : "Easy";
      showToast(isOn ? "Easy Mode enabled." : "Easy Mode disabled.");
    });
  }
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", body.classList.contains("theme-light") ? "true" : "false");
    themeToggle.addEventListener("click", () => {
      body.classList.toggle("theme-light");
      const mode = body.classList.contains("theme-light") ? "light" : "dark";
      localStorage.setItem("theme_mode", mode);
      themeToggle.setAttribute("aria-pressed", mode === "light" ? "true" : "false");
      showToast(mode === "light" ? "Light mode enabled." : "Dark mode enabled.");
    });
  }

  const toastCode = params.get("toast");
  if (toastCode && toastMap[toastCode]) {
    showToast(toastMap[toastCode]);
    params.delete("toast");
    const query = params.toString();
    history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
  }

  document.querySelectorAll("[data-skeleton]").forEach((el) => {
    el.classList.add("is-loading");
    setTimeout(() => el.classList.remove("is-loading"), 180);
  });

  const densityToggle = qs("density-toggle");
  const storedDensity = localStorage.getItem("density_mode");
  if (storedDensity === "dense") {
    body.classList.add("density-dense");
  }
  if (densityToggle) {
    densityToggle.textContent = body.classList.contains("density-dense") ? "Dense" : "Calm";
    densityToggle.addEventListener("click", () => {
      body.classList.toggle("density-dense");
      const mode = body.classList.contains("density-dense") ? "dense" : "calm";
      localStorage.setItem("density_mode", mode);
      densityToggle.textContent = mode === "dense" ? "Dense" : "Calm";
      showToast(mode === "dense" ? "Density set to Dense." : "Density set to Calm.");
      const menu = densityToggle.closest("details");
      if (menu) menu.open = false;
    });
  }

  const overlay = qs("tactical-overlay");
  const panel = qs("tactical-panel");
  const panelTitle = qs("panel-title");
  const panelMeta = qs("panel-meta");
  const panelDetail = qs("panel-detail");
  const panelClose = qs("panel-close");

  function closePanel() {
    if (!panel || !overlay) return;
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    overlay.hidden = true;
  }

  function openPanel(title, meta, details, contacts, quickData) {
    if (!panel || !overlay || !panelTitle || !panelMeta || !panelDetail) return;
    panelTitle.textContent = title || "Quick View";
    panelMeta.textContent = meta || "";
    const email = quickData && quickData.email ? quickData.email : "";
    const phone = quickData && quickData.phone ? quickData.phone : "";
    const approvals = quickData && typeof quickData.approvals === "number" ? quickData.approvals : null;
    const blocked = quickData && typeof quickData.blocked === "number" ? quickData.blocked : null;
    const due = quickData && typeof quickData.due === "number" ? quickData.due : null;
    const riskScore = quickData && typeof quickData.risk_score === "number" ? quickData.risk_score : null;
    const riskLevel = quickData && quickData.risk_level ? quickData.risk_level : null;
    const drivers = quickData && Array.isArray(quickData.drivers) ? quickData.drivers : [];
    const mrrCents = quickData && typeof quickData.mrr_cents === "number" ? quickData.mrr_cents : null;
    const openClientUrl = quickData && quickData.open_client_url ? quickData.open_client_url : `/clients?tenant_id=${encodeURIComponent(tenantId)}`;
    const openProjectsUrl = quickData && quickData.open_projects_url ? quickData.open_projects_url : `/projects?tenant_id=${encodeURIComponent(tenantId)}`;

    const detailHtml = `
      <p>${escapeHtml(details || "No additional details yet.")}</p>
      <h3>Contacts</h3>
      ${contacts && contacts.length ? `<ul class="list">${contacts.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : '<p class="subtle">No contact records yet. Add from CRM.</p>'}
      <div class="quick-actions">
        ${phone ? `<a class="chip-link" href="tel:${escapeHtml(phone)}">Call</a>` : '<span class="subtle">Add contact info</span>'}
        ${email ? `<a class="chip-link" href="mailto:${escapeHtml(email)}">Email</a>` : ""}
        ${phone ? `<a class="chip-link" href="sms:${escapeHtml(phone)}">Text</a>` : ""}
      </div>
      <h3>Quick actions</h3>
      ${
        approvals !== null || blocked !== null || due !== null
          ? `<ul class="list">
          <li><span>Approvals pending</span><span class="status-chip status-due">${approvals ?? 0}</span></li>
          <li><span>Blocked runs</span><span class="status-chip status-blocked">${blocked ?? 0}</span></li>
          <li><span>Due tasks</span><span class="status-chip status-risk">${due ?? 0}</span></li>
        </ul>`
          : '<p class="subtle">No tracked actions yet.</p>'
      }
      ${
        riskScore !== null
          ? `<h3>Client health</h3><p class="subtle">Risk: ${escapeHtml(riskLevel || "—")} (${riskScore}) · MRR: ${mrrCents !== null ? `$${(mrrCents / 100).toFixed(2)}` : "—"}</p>`
          : ""
      }
      ${
        drivers.length
          ? `<ul class="list">${drivers.map((d) => `<li>${escapeHtml(d)}</li>`).join("")}</ul>`
          : ""
      }
      <div class="quick-actions">
        <a class="chip-link" href="${escapeHtml(openClientUrl)}">Open Client</a>
        <a class="chip-link" href="${escapeHtml(openProjectsUrl)}">Open Projects</a>
      </div>
    `;
    panelDetail.innerHTML = detailHtml;
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    overlay.hidden = false;
  }

  document.querySelectorAll("[data-quick-view]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const contacts = (btn.dataset.contacts || "")
        .split("||")
        .map((x) => x.trim())
        .filter(Boolean);
      let quickData = null;
      const clientId = btn.dataset.clientId;
      if (clientId) {
        try {
          const response = await fetch(`/clients/${encodeURIComponent(clientId)}/quickview?tenant_id=${encodeURIComponent(tenantId)}`);
          if (response.ok) quickData = await response.json();
        } catch (err) {
          quickData = null;
        }
      }
      openPanel(btn.dataset.title || "Quick View", btn.dataset.meta || "", btn.dataset.details || "", contacts, quickData);
    });
  });

  if (panelClose) panelClose.addEventListener("click", closePanel);
  if (overlay) overlay.addEventListener("click", closePanel);

  const focusToggle = qs("focus-mode-toggle");
  const intelligenceCol = qs("intelligence-col");
  const sectionsToHide = Array.from(document.querySelectorAll("[data-focus-hide]"));
  if (focusToggle) {
    let focusMode = false;
    focusToggle.addEventListener("click", () => {
      focusMode = !focusMode;
      body.classList.toggle("focus-mode", focusMode);
      if (intelligenceCol) intelligenceCol.style.display = focusMode ? "none" : "";
      sectionsToHide.forEach((el) => {
        el.style.display = focusMode ? "none" : "";
      });
      focusToggle.textContent = focusMode ? "Exit Focus" : "Focus Mode";
    });
  }

  const feedFilters = document.querySelectorAll("[data-feed-filter]");
  const feedRows = document.querySelectorAll("[data-feed-kind]");
  const muteBtn = qs("feed-mute");
  const mutedFeedKey = `muted_feed_${tenantId}`;
  const mutedIds = new Set(JSON.parse(localStorage.getItem(mutedFeedKey) || "[]"));
  feedRows.forEach((row) => {
    const id = row.dataset.feedId;
    if (id && mutedIds.has(id)) row.hidden = true;
  });
  let feedMuted = false;
  if (feedFilters.length) {
    feedFilters.forEach((chip) => {
      chip.addEventListener("click", () => {
        const key = chip.dataset.feedFilter;
        const isActive = chip.classList.toggle("active");
        if (key === "all") {
          feedFilters.forEach((el) => {
            if (el !== chip) el.classList.remove("active");
          });
          feedRows.forEach((row) => {
            row.hidden = false;
          });
          chip.classList.add("active");
          return;
        }
        const active = Array.from(feedFilters)
          .filter((el) => el !== chip && el.dataset.feedFilter !== "all" && el.classList.contains("active"))
          .map((el) => el.dataset.feedFilter);
        if (isActive && !active.includes(key)) active.push(key);
        if (!active.length) {
          const all = document.querySelector('[data-feed-filter="all"]');
          if (all) all.classList.add("active");
          feedRows.forEach((row) => {
            row.hidden = false;
          });
          return;
        }
        const all = document.querySelector('[data-feed-filter="all"]');
        if (all) all.classList.remove("active");
        feedRows.forEach((row) => {
          row.hidden = !active.includes(row.dataset.feedKind);
        });
      });
    });
  }
  if (muteBtn) {
    muteBtn.addEventListener("click", () => {
      feedMuted = !feedMuted;
      muteBtn.textContent = feedMuted ? "Unmute" : "Mute";
      if (feedMuted) {
        feedRows.forEach((row) => {
          if (!row.hidden && row.dataset.feedId) mutedIds.add(row.dataset.feedId);
        });
        localStorage.setItem(mutedFeedKey, JSON.stringify(Array.from(mutedIds)));
        feedRows.forEach((row) => {
          if (row.dataset.feedId && mutedIds.has(row.dataset.feedId)) row.hidden = true;
        });
      } else {
        mutedIds.clear();
        localStorage.setItem(mutedFeedKey, "[]");
        feedRows.forEach((row) => {
          row.hidden = false;
        });
      }
      showToast(feedMuted ? "Feed muted and saved." : "Feed unmuted.");
    });
  }

  const palette = qs("command-palette");
  const commandInput = qs("command-input");
  const commandResults = qs("command-results");
  const commandClose = qs("command-close");
  let selectedIndex = 0;
  let results = [];
  let searchTimer = null;

  function resetPaletteState() {
    if (!palette) return;
    palette.hidden = true;
    palette.setAttribute("aria-hidden", "true");
    body.classList.remove("overlay-open");
  }

  function navigateFromPalette(url) {
    if (!url) {
      closePalette();
      return;
    }
    closePalette();
    // Give close transition a tick so overlay never appears stuck.
    setTimeout(() => {
      window.location.href = url;
    }, 10);
  }

  function renderPaletteResults(items, loading) {
    if (!commandResults) return;
    if (loading) {
      commandResults.innerHTML = `
        <li class="palette-item skeleton-line"></li>
        <li class="palette-item skeleton-line"></li>
        <li class="palette-item skeleton-line"></li>
      `;
      return;
    }
    results = items;
    selectedIndex = 0;
    commandResults.innerHTML = results
      .map(
        (item, i) => `
        <li class="palette-item ${i === selectedIndex ? "selected" : ""}" role="option" aria-selected="${i === selectedIndex ? "true" : "false"}">
          <button type="button" class="palette-btn" data-index="${i}">
            <span>${escapeHtml(item.title)}</span>
            <small>${escapeHtml(item.subtitle || item.type || "")}</small>
          </button>
        </li>
      `
      )
      .join("");
    commandResults.querySelectorAll(".palette-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.dataset.index || 0);
        const entry = results[i];
        if (entry) navigateFromPalette(entry.url);
      });
    });
  }

  function fuzzyScore(query, text) {
    if (!query) return 1;
    const q = query.toLowerCase();
    const t = (text || "").toLowerCase();
    if (t.includes(q)) return 100 - (t.indexOf(q) || 0);
    let qi = 0;
    for (let i = 0; i < t.length && qi < q.length; i += 1) {
      if (t[i] === q[qi]) qi += 1;
    }
    return qi === q.length ? 60 : 0;
  }

  function renderPaletteGrouped(data, query) {
    if (!commandResults) return;
    const commands = (data.commands || [])
      .map((x) => ({ type: "command", title: x.title, subtitle: "Command", url: x.url, score: fuzzyScore(query, x.title) }))
      .filter((x) => x.score > 0 || !query)
      .sort((a, b) => b.score - a.score);
    const clients = (data.clients || [])
      .map((x) => ({ type: "client", title: x.name, subtitle: "Client", url: x.url, score: fuzzyScore(query, x.name) }))
      .filter((x) => x.score > 0 || !query)
      .sort((a, b) => b.score - a.score);
    const projects = (data.projects || [])
      .map((x) => ({ type: "project", title: x.name, subtitle: `Project · ${x.client_name || "—"}`, url: x.url, score: fuzzyScore(query, x.name) }))
      .filter((x) => x.score > 0 || !query)
      .sort((a, b) => b.score - a.score);

    const grouped = [
      { label: "Commands", items: commands },
      { label: "Clients", items: clients },
      { label: "Projects", items: projects },
    ];
    results = grouped.flatMap((group) => group.items);
    selectedIndex = 0;
    if (!results.length) {
      commandResults.innerHTML = '<li class="palette-empty">No results</li>';
      return;
    }
    let flatIndex = 0;
    commandResults.innerHTML = grouped
      .map((group) => {
        if (!group.items.length) return "";
        const rows = group.items
          .map((item) => {
            const idx = flatIndex;
            flatIndex += 1;
            return `
              <li class="palette-item ${idx === selectedIndex ? "selected" : ""}" role="option" aria-selected="${idx === selectedIndex ? "true" : "false"}">
                <button type="button" class="palette-btn" data-index="${idx}">
                  <span>${escapeHtml(item.title)}</span>
                  <small>${escapeHtml(item.subtitle)}</small>
                </button>
              </li>
            `;
          })
          .join("");
        return `<li class="palette-group-label">${group.label}</li>${rows}`;
      })
      .join("");
    commandResults.querySelectorAll(".palette-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.dataset.index || 0);
        const entry = results[i];
        if (entry) navigateFromPalette(entry.url);
      });
    });
  }

  async function fetchSearch(query) {
    if (!commandInput) return;
    renderPaletteResults([], true);
    try {
      const response = await fetch(`/search?tenant_id=${encodeURIComponent(tenantId)}&q=${encodeURIComponent(query)}`);
      const data = await response.json();
      renderPaletteGrouped(data, query);
    } catch (err) {
      renderPaletteResults(
        [
          {
            title: "Search unavailable",
            subtitle: "Press Esc to close and refresh once.",
            url: "",
          },
        ],
        false
      );
    }
  }

  function openPalette() {
    if (!palette || !commandInput) return;
    palette.hidden = false;
    palette.setAttribute("aria-hidden", "false");
    body.classList.add("overlay-open");
    commandInput.value = "";
    commandInput.focus();
    fetchSearch("");
  }

  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    palette.setAttribute("aria-hidden", "true");
    body.classList.remove("overlay-open");
  }

  if (palette) {
    palette.addEventListener("click", (e) => {
      if (e.target === palette) closePalette();
    });
  }
  const commandOpen = qs("command-open");
  if (commandOpen) commandOpen.addEventListener("click", openPalette);
  if (commandClose) commandClose.addEventListener("click", closePalette);

  if (commandInput) {
    commandInput.addEventListener("input", () => {
      const val = commandInput.value.trim();
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        fetchSearch(val);
      }, 120);
    });
  }

  function moveSelection(next) {
    if (!results.length || !commandResults) return;
    selectedIndex = (selectedIndex + next + results.length) % results.length;
    commandResults.querySelectorAll(".palette-item").forEach((item, idx) => {
      item.classList.toggle("selected", idx === selectedIndex);
      item.setAttribute("aria-selected", idx === selectedIndex ? "true" : "false");
    });
  }

  document.addEventListener("keydown", (e) => {
    const isMetaK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
    if (isMetaK) {
      e.preventDefault();
      if (palette && !palette.hidden) {
        closePalette();
      } else {
        openPalette();
      }
      return;
    }
    if (e.key === "Escape") {
      closePalette();
      closePanel();
      return;
    }
    if (palette && !palette.hidden) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        moveSelection(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        moveSelection(-1);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const entry = results[selectedIndex];
        if (entry) navigateFromPalette(entry.url);
      }
    }
  });

  document.addEventListener("click", (e) => {
    document.querySelectorAll("details.action-menu, details.chip-submenu").forEach((menu) => {
      if (!menu.contains(e.target)) menu.open = false;
    });
  });

  // Hard reset for reloads/bfcache restores to prevent stuck overlay state.
  resetPaletteState();
  window.addEventListener("pageshow", resetPaletteState);

  const openIntent = params.get("open");
  if (openIntent === "new-client") {
    const input = document.querySelector('form[action^="/clients"] input[name="name"]');
    if (input) input.focus();
  } else if (openIntent === "new-project") {
    const input = document.querySelector('form[action^="/projects"] input[name="name"]');
    if (input) input.focus();
  } else if (openIntent === "new-campaign") {
    const input = document.querySelector('form[action^="/marketing/plan"] input[name="budget"]');
    if (input) input.focus();
  } else if (openIntent === "create-workflow") {
    const input = document.querySelector('form[action^="/workflows"] input[name="name"]');
    if (input) input.focus();
  }

  const quickClientId = params.get("quick_client_id");
  if (quickClientId) {
    const trigger = document.querySelector(`[data-quick-view][data-client-id="${quickClientId}"]`);
    if (trigger) trigger.click();
  }

  function setupDnD(options) {
    const board = document.querySelector(options.boardSelector);
    if (!board) return;
    const laneSelector = options.laneSelector;
    const cardSelector = options.cardSelector;
    let dragEl = null;
    let dragId = null;
    let sourceLaneValue = null;

    board.querySelectorAll(cardSelector).forEach((card) => {
      card.draggable = true;
      card.addEventListener("dragstart", () => {
        dragEl = card;
        dragId = card.dataset[options.cardIdDataset];
        const lane = card.closest(laneSelector);
        sourceLaneValue = lane ? lane.dataset[options.laneDataset] : null;
        card.classList.add("dragging");
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        board.querySelectorAll(laneSelector).forEach((l) => l.classList.remove("lane-over"));
      });
    });

    board.querySelectorAll(laneSelector).forEach((lane) => {
      lane.addEventListener("dragover", (e) => {
        e.preventDefault();
        lane.classList.add("lane-over");
      });
      lane.addEventListener("dragleave", () => {
        lane.classList.remove("lane-over");
      });
      lane.addEventListener("drop", async (e) => {
        e.preventDefault();
        lane.classList.remove("lane-over");
        if (!dragEl || !dragId) return;
        const targetValue = lane.dataset[options.laneDataset];
        if (!targetValue || targetValue === sourceLaneValue) return;

        const bodyParams = new URLSearchParams();
        bodyParams.set(options.fieldName, targetValue);
        try {
          const response = await fetch(`${options.endpoint(dragId)}?tenant_id=${encodeURIComponent(tenantId)}`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: bodyParams.toString(),
          });
          if (!response.ok) throw new Error(`Update failed (${response.status})`);
          showToast(options.successToast(targetValue));
          // Keep behavior deterministic with server ordering and empty-state handling.
          window.location.reload();
        } catch (err) {
          showToast("Could not update lane. Try again.");
        }
      });
    });
  }

  setupDnD({
    boardSelector: '[data-board="tasks"]',
    laneSelector: "[data-task-lane]",
    cardSelector: "[data-task-id]",
    cardIdDataset: "taskId",
    laneDataset: "taskLane",
    fieldName: "status",
    endpoint: (id) => `/tasks/${id}/status`,
    successToast: (status) => `Task moved to ${status.replaceAll("_", " ")}.`,
  });

  setupDnD({
    boardSelector: '[data-board="scheduler"]',
    laneSelector: "[data-service-stage]",
    cardSelector: "[data-service-id]",
    cardIdDataset: "serviceId",
    laneDataset: "serviceStage",
    fieldName: "stage",
    endpoint: (id) => `/service-jobs/${id}/stage`,
    successToast: (stage) => `Service moved to ${stage.replaceAll("_", " ")}.`,
  });

  const platformEl = qs("marketing-platform");
  const objectiveEl = qs("marketing-objective");
  const subOptionEl = qs("marketing-sub-option");
  const templateNameEl = qs("marketing-template-name");
  const selectedTemplateLabel = qs("selected-template-label");
  const platformDataEl = qs("platform-objectives-data");
  const platformConfigEl = qs("platform-config-data");
  const platformHelp = qs("platform-help");
  const templatesEl = qs("platform-templates");
  if (platformEl && objectiveEl && platformDataEl) {
    let platformObjectives = {};
    let platformConfig = {};
    try {
      platformObjectives = JSON.parse(platformDataEl.textContent || "{}");
    } catch (err) {
      platformObjectives = {};
    }
    if (platformConfigEl) {
      try {
        platformConfig = JSON.parse(platformConfigEl.textContent || "{}");
      } catch (err) {
        platformConfig = {};
      }
    }
    const platformCopy = {
      "Google Ads": "Google Ads: choose Search/Performance Max style based on conversion maturity.",
      "Meta Ads": "Meta Ads: pick objective first, then align creative format and placement strategy.",
      "LinkedIn Ads": "LinkedIn Ads: use high-intent B2B audiences and lead forms for lower friction.",
      "Microsoft Ads": "Microsoft Ads: mirror top Google intent, then optimize by audience network behavior.",
      "YouTube Ads": "YouTube Ads: choose between Views, Reach, Sequence, or Video Action based on goal.",
      "TikTok Ads": "TikTok Ads: objective + creative cadence drive performance more than narrow targeting.",
      "X Ads": "X Ads: use website click or video structures around real-time intent clusters.",
      "Pinterest Ads": "Pinterest Ads: map intent-driven creatives to consideration vs conversion goals.",
      "Reddit Ads": "Reddit Ads: align subreddit context with clear CTA and landing page relevance.",
      "Snapchat Ads": "Snapchat Ads: pick reach/story vs lead/app goals and tune after early signal.",
    };

    function renderTemplates(currentPlatform) {
      if (!templatesEl) return;
      const templates = platformConfig[currentPlatform] && platformConfig[currentPlatform].templates ? platformConfig[currentPlatform].templates : [];
      if (!templates.length) {
        templatesEl.innerHTML = '<li><span>No templates available</span><span class="subtle">Use custom setup</span></li>';
        return;
      }
      templatesEl.innerHTML = templates
        .map(
          (template) => `
          <li>
            <span>${escapeHtml(template)}</span>
            <button type="button" class="chip-link use-template-btn" data-template-name="${escapeHtml(template)}">Use Template</button>
          </li>`
        )
        .join("");
      templatesEl.querySelectorAll(".use-template-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const chosen = btn.dataset.templateName || "";
          if (templateNameEl) templateNameEl.value = chosen;
          if (selectedTemplateLabel) selectedTemplateLabel.textContent = chosen ? `Selected template: ${chosen}` : "No template selected yet.";
          showToast(`Template selected: ${chosen}`);
        });
      });
    }

    function rebuildSubOptions() {
      if (!subOptionEl) return;
      const currentPlatform = platformEl.value;
      const currentObjective = objectiveEl.value;
      const options = platformConfig[currentPlatform] && platformConfig[currentPlatform].sub_options ? platformConfig[currentPlatform].sub_options[currentObjective] || [] : [];
      const currentValue = subOptionEl.value;
      subOptionEl.innerHTML = '<option value="">Auto-select best option</option>';
      options.forEach((item) => {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        subOptionEl.appendChild(option);
      });
      if (options.includes(currentValue)) {
        subOptionEl.value = currentValue;
      }
    }

    function rebuildObjectives() {
      const currentPlatform = platformEl.value;
      const allowed = platformObjectives[currentPlatform] || [];
      const currentObjective = objectiveEl.value;
      if (!allowed.length) return;
      objectiveEl.innerHTML = allowed.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join("");
      if (allowed.includes(currentObjective)) objectiveEl.value = currentObjective;
      if (platformHelp) platformHelp.textContent = platformCopy[currentPlatform] || "Use platform-specific settings, then validate after launch.";
      rebuildSubOptions();
      renderTemplates(currentPlatform);
    }

    platformEl.addEventListener("change", rebuildObjectives);
    objectiveEl.addEventListener("change", rebuildSubOptions);
    rebuildObjectives();
  }

  const campaignForm = qs("campaign-plan-form");
  if (campaignForm) {
    campaignForm.addEventListener("submit", () => {
      const websiteInput = campaignForm.querySelector('input[name="website_url"]');
      if (!websiteInput) return;
      const raw = (websiteInput.value || "").trim();
      if (!raw) return;
      if (!/^https?:\/\//i.test(raw)) websiteInput.value = `https://${raw}`;
    });
  }
})();
