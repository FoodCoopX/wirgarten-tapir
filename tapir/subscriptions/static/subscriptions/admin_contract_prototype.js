(() => {
  const modal = document.getElementById("admin-contract-modal");
  if (!modal) return;
  const body = document.getElementById("ac-content");
  const next = document.getElementById("ac-next");
  const back = document.getElementById("ac-back");
  const error = document.getElementById("ac-error");
  const hint = document.getElementById("ac-hint");
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const date = (value) => (value ? value.split("-").reverse().join(".") : "–");
  let flow = "combined";
  let config,
    member,
    step = 0,
    contract = null,
    data = {},
    capacity = null,
    requestNumber = 0,
    searchNumber = 0;
  const api = async (params) => {
    const response = await fetch(
      `${modal.dataset.endpoint}?${new URLSearchParams(params)}`,
      { headers: { Accept: "application/json" } },
    );
    if (!response.ok)
      throw new Error(
        "Die Daten konnten nicht geprüft werden. Bitte Eingaben prüfen oder erneut versuchen.",
      );
    return response.json();
  };
  function fail(message) {
    error.textContent = message;
    error.hidden = false;
  }
  function statusIcon(present) {
    return `<span class="material-icons ac-status-icon ${present ? "text-success" : "text-danger"}" role="img" aria-label="${present ? "Vorhanden" : "Fehlt"}">${present ? "check_circle" : "cancel"}</span>`;
  }
  function memberSummary() {
    return `<div class="ac-member d-flex justify-content-between align-items-center"><div><strong>${esc(member.name)}</strong><div class="small text-muted">Mitglied ${esc(member.number)}</div></div>${step === 0 ? '<button class="btn btn-sm btn-outline-secondary" id="ac-change-member">Anderes Mitglied</button>' : ""}</div>`;
  }
  function frame() {
    modal.dispatchEvent(new Event("tapir:prototype-before-render"));
    error.hidden = true;
    document.getElementById("admin-contract-title").textContent =
      flow === "new"
        ? "Vertrag hinzufügen"
        : flow === "change"
          ? "Anteilsgröße zu einem bestimmten Datum verändern"
          : "Vertrag hinzufügen oder ändern";
    const steps = [
      flow === "new"
        ? "Mitglied"
        : flow === "change"
          ? "Mitglied & Anteil"
          : "Mitglied & Vertrag",
      flow === "change" ? "Anteilsgröße & Datum" : "Vertragsdaten",
      "Zusammenfassung",
    ];
    modal.querySelectorAll("[data-step]").forEach((el, index) => {
      el.textContent = `${index + 1} · ${steps[index]}`;
    });
    modal.querySelector(".modal-body").scrollTop = 0;
    modal.querySelectorAll("[data-step]").forEach((el) => {
      el.classList.toggle("active", Number(el.dataset.step) === step);
      el.setAttribute(
        "aria-current",
        Number(el.dataset.step) === step ? "step" : "false",
      );
    });
    back.innerHTML = `<span class="material-icons" aria-hidden="true">${step === 0 ? "close" : "arrow_back"}</span><span>${step === 0 ? "Abbrechen" : "Zurück"}</span>`;
    next.innerHTML = `<span class="material-icons" aria-hidden="true">${step === 2 ? "done" : "arrow_forward"}</span><span>${[flow === "change" ? "Weiter zu Anteilsgröße und Datum" : "Weiter zu den Vertragsdaten", flow === "new" ? "Vertrag prüfen" : "Änderung prüfen", "Vorschau abschließen"][step]}</span>`;
    hint.textContent = `Schritt ${step + 1} von 3`;
    next.disabled = true;
  }
  function selectMember() {
    step = 0;
    member = null;
    contract = null;
    frame();
    body.innerHTML = `<h5>Für welches Mitglied?</h5><label class="form-label" for="ac-search">Mitglied suchen</label><input id="ac-search" class="form-control" type="search" placeholder="Mitgliedsnummer, Vorname oder Nachname" autocomplete="off"><div class="form-text mb-3">Mindestens zwei Zeichen. Vor- und Nachname können kombiniert werden.</div><div id="ac-results" class="list-group" aria-live="polite"></div>`;
    const input = document.getElementById("ac-search");
    let timer;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      const sequence = ++searchNumber;
      const query = input.value.trim();
      const results = document.getElementById("ac-results");
      results.innerHTML = "";
      if (query.length < 2) return;
      timer = setTimeout(async () => {
        try {
          const matches = await api({ q: query });
          if (
            sequence !== searchNumber ||
            !document.getElementById("ac-search")
          )
            return;
          results.innerHTML = matches.length
            ? matches
                .map(
                  (m) =>
                    `<button type="button" class="list-group-item list-group-item-action d-flex justify-content-between py-3" data-member="${esc(m.id)}"><strong>${esc(m.name)}</strong><span class="text-muted">${esc(m.number)}</span></button>`,
                )
                .join("")
            : '<div class="list-group-item text-muted">Kein passendes Mitglied gefunden.</div>';
          results.querySelectorAll("[data-member]").forEach((button) =>
            button.addEventListener("click", async () => {
              try {
                button.disabled = true;
                member = await api({ member: button.dataset.member });
                if (flow === "new") details(true);
                else showContracts();
              } catch (e) {
                fail(e.message);
                button.disabled = false;
              }
            }),
          );
        } catch (e) {
          if (sequence === searchNumber) fail(e.message);
        }
      }, 250);
    });
    input.focus();
  }
  function showContracts() {
    frame();
    body.innerHTML =
      memberSummary() +
      `<h5>Was möchtest du tun?</h5><p class="text-muted">Neuen Vertrag hinzufügen oder einen bestehenden Vertrag zu einem bestimmten Datum verändern.</p><div class="row g-3 ac-decisions"><div class="col-md-6"><section class="ac-contract ac-decision h-100 mb-0"><div class="d-flex justify-content-between align-items-start gap-2"><label for="ac-action-new"><input id="ac-action-new" class="form-check-input me-2" type="radio" name="ac-action" value="new" checked><strong>Neuen Vertrag hinzufügen</strong></label><span class="d-inline-flex" role="group" aria-label="Hilfe: Neuen Vertrag hinzufügen" data-admin-contract-help data-help-title="Neuen Vertrag hinzufügen" data-help-text="Du legst einen zusätzlichen Produktvertrag an und wählst dafür Vertragsart, Produktanteilsgröße, Menge und Beginn. Beispiel: Zu einem bestehenden M-Anteil kommt ab dem gewählten Datum ein weiterer L-Anteil hinzu."></span></div><div class="small text-muted ms-4 mt-2">Zu einem ausgewählten Datum und zusätzlich zu den bestehenden Verträgen.</div></section></div><div class="col-md-6"><section class="ac-decision border rounded p-3 h-100" aria-label="Einen bestehenden Vertrag ändern"><div class="d-flex justify-content-between align-items-start gap-2"><h6 class="mb-2">Einen bestehenden Vertrag ändern</h6><span class="d-inline-flex" role="group" aria-label="Hilfe: Einen bestehenden Vertrag ändern" data-admin-contract-help data-help-title="Einen bestehenden Vertrag ändern" data-help-text="Wähle genau einen bestehenden Anteil aus und ändere dessen Produktanteilsgröße ab einem ausgewählten Datum. Vertragsart und Anzahl der Anteile bleiben gleich. Beispiel: Ein M-Anteil wird zu einem L-Anteil. Gekündigte oder beendete Verträge können nicht geändert werden."></span></div><p class="small text-muted">Wähle den einzelnen Anteil aus, dessen Größe du zu einem bestimmten Datum verändern möchtest.</p><div class="ac-existing-contracts">` +
      (member.contracts.length
        ? member.contracts
            .map(
              (c) =>
                `<label class="ac-contract ${c.cancelled || c.ended ? "disabled" : ""}"><div class="d-flex justify-content-between gap-3"><div><input class="form-check-input me-2" type="radio" name="ac-action" value="${esc(c.selectionId)}" ${c.cancelled || c.ended ? "disabled" : ""}><strong>${esc(c.type)} · ${esc(c.product)}${c.originalQuantity > 1 ? ` · Anteil ${c.unit} von ${c.originalQuantity}` : ""}</strong></div><span class="badge ${c.cancelled || c.ended ? "text-bg-secondary" : "text-bg-success"}">${c.cancelled ? "Gekündigt" : c.ended ? "Beendet" : "Laufend / geplant"}</span></div><div class="small text-muted ms-4 mt-1">${date(c.start)} – ${date(c.end)}${c.cancelled || c.ended ? " · Dieser Vertrag kann nicht mehr geändert werden." : ""}</div>${c.priceCategory === "exempt" ? '<div class="ms-4 mt-2"><span class="badge text-bg-warning">Beitragsbefreit</span></div>' : c.priceCategory === "custom" ? '<div class="ms-4 mt-2"><span class="badge text-bg-info">Personalisierter Betrag</span></div>' : ""}</label>`,
            )
            .join("")
        : '<p class="text-muted">Dieses Mitglied hat noch keine Produktverträge.</p>') +
      `</div></section></div></div><ul class="list-unstyled small mt-3 mb-0 d-flex flex-column gap-2" aria-label="Hinterlegte Mitgliedsdaten">${[
        [
          "Abholort",
          member.location?.name || "Noch nicht hinterlegt",
          Boolean(member.location),
        ],
        [
          "Bankdaten",
          member.bankPresent ? "Vorhanden" : "Fehlen",
          member.bankPresent,
        ],
        [
          "Zahlungsintervall",
          member.rhythm || "Nicht hinterlegt",
          Boolean(member.rhythm),
        ],
      ]
        .map(
          ([label, value, present]) =>
            `<li class="d-flex align-items-center gap-2">${statusIcon(present)}<span>${label}: <strong>${esc(value)}</strong></span></li>`,
        )
        .join("")}</ul>`;
    if (flow === "change") {
      const columns = body.querySelector(".ac-decisions");
      columns.firstElementChild.remove();
      columns.firstElementChild.className = "col-12";
      body.querySelector("h5").textContent =
        "Welchen Anteil möchtest du ändern?";
      body.querySelector("h5 + p").textContent =
        "Wähle genau einen bestehenden Anteil aus. Im nächsten Schritt legst du die neue Größe und das Änderungsdatum fest.";
      if (!member.contracts.some((c) => !c.cancelled && !c.ended)) {
        columns.insertAdjacentHTML(
          "beforeend",
          '<p class="text-muted mt-3">Für dieses Mitglied ist kein änderbarer Anteil vorhanden.</p>',
        );
      }
    }
    modal.dispatchEvent(new Event("tapir:prototype-rendered"));
    document.getElementById("ac-change-member").onclick = selectMember;
    body.querySelectorAll('[name="ac-action"]').forEach(
      (input) =>
        (input.onchange = () => {
          contract =
            member.contracts.find((c) => c.selectionId === input.value) || null;
          if (flow === "change") next.disabled = !contract;
        }),
    );
    contract = null;
    next.disabled = flow === "change";
  }
  function monday(week) {
    if (!/^\d{4}-W\d{2}$/.test(week)) return "";
    const [year, number] = week.split("-W").map(Number);
    const d = new Date(Date.UTC(year, 0, 4));
    d.setUTCDate(d.getUTCDate() - (d.getUTCDay() || 7) + 1 + (number - 1) * 7);
    return d.toISOString().slice(0, 10);
  }
  function availableWeeks() {
    const current = config.periods.find(
      (p) => p.start <= config.today && p.end >= config.today,
    );
    if (!current || !config.minWeek) return [];
    const weeks = [];
    const day = new Date(`${monday(config.minWeek)}T00:00:00Z`);
    while (day.toISOString().slice(0, 10) <= current.end) {
      const start = day.toISOString().slice(0, 10);
      if (start >= current.start) {
        const thursday = new Date(day);
        thursday.setUTCDate(thursday.getUTCDate() + 3);
        const year = thursday.getUTCFullYear();
        const firstMonday = new Date(`${monday(`${year}-W01`)}T00:00:00Z`);
        const number = Math.round((day - firstMonday) / 604800000) + 1;
        weeks.push({
          year: String(year),
          number,
          value: `${year}-W${String(number).padStart(2, "0")}`,
          start,
        });
      }
      day.setUTCDate(day.getUTCDate() + 7);
    }
    return weeks;
  }
  function weekOptions(weeks, year) {
    return (
      '<option value="">Kalenderwoche wählen …</option>' +
      weeks
        .filter((w) => w.year === year)
        .map(
          (w) =>
            `<option value="${w.value}" ${w.value === data.week ? "selected" : ""}>KW ${w.number} · Montag, ${date(w.start)}</option>`,
        )
        .join("")
    );
  }
  function startDate() {
    if (data.startMode === "week") return monday(data.week || "");
    if (data.startMode === "period")
      return config.periods.find((p) => p.start > config.today)?.start || "";
    return config.nextStart;
  }
  function validBank() {
    if (member.bankPresent) return true;
    const iban = (data.iban || "").replace(/\s/g, "").toUpperCase();
    if (
      !(data.owner || "").trim() ||
      !/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(iban)
    )
      return false;
    const rotated = (iban.slice(4) + iban.slice(0, 4)).replace(
      /[A-Z]/g,
      (c) => c.charCodeAt(0) - 55,
    );
    let remainder = 0;
    for (const digit of rotated)
      remainder = (remainder * 10 + Number(digit)) % 97;
    return remainder === 1;
  }
  function updateNext() {
    const location = member.location?.id || data.location;
    next.disabled =
      !capacity ||
      !capacity.globalOkay ||
      !capacity.productOkay ||
      !capacity.locations.some((l) => l.id === location) ||
      !validBank() ||
      (!member.rhythm && !data.rhythm);
  }
  async function check() {
    const sequence = ++requestNumber;
    capacity = null;
    next.disabled = true;
    const status = document.getElementById("ac-capacity");
    status.className = "alert alert-light border";
    status.textContent = "Kapazitäten werden anhand der Testdaten geprüft …";
    const start = startDate();
    const weekField = document.getElementById("ac-week");
    const inPast = Boolean(start && start < config.today);
    weekField.classList.toggle(
      "is-invalid",
      data.startMode === "week" && inPast,
    );
    weekField.setAttribute(
      "aria-invalid",
      String(data.startMode === "week" && inPast),
    );
    document.getElementById("ac-effective-date").textContent = "";
    if (data.startMode === "week" && !data.week) {
      status.className = "alert alert-light border";
      status.textContent = data.weekYear
        ? "Bitte eine Kalenderwoche auswählen."
        : "Bitte zuerst das Jahr und danach die Kalenderwoche auswählen.";
      return;
    }
    if (inPast) {
      status.className = "alert alert-warning";
      status.textContent =
        "Der Vertragsbeginn darf nicht in der Vergangenheit liegen.";
      return;
    }
    const current = config.periods.find(
      (p) => p.start <= config.today && p.end >= config.today,
    );
    if (
      !Number.isInteger(Number(data.quantity)) ||
      Number(data.quantity) < 1 ||
      Number(data.quantity) > 32767 ||
      !start ||
      (data.startMode === "week" &&
        (!current || start < current.start || start > current.end))
    ) {
      status.className = "alert alert-warning";
      status.textContent =
        "Bitte eine ganze Menge ab 1 und einen gültigen Vertragsbeginn wählen. Die Kalenderwoche muss in der aktuellen Vertragsperiode liegen.";
      return;
    }
    document.getElementById("ac-effective-date").textContent =
      `Wirksam ab Montag, ${date(start)}${data.startMode === "period" ? " (Beginn der nächsten Vertragsperiode)" : ""}`;
    // A growing period can begin on a weekday other than Monday.
    if (data.startMode === "period")
      document.getElementById("ac-effective-date").textContent =
        `Wirksam ab ${date(start)} · Beginn der nächsten Vertragsperiode`;
    try {
      const result = await api({
        check: "1",
        member: member.id,
        product: data.product,
        quantity: data.quantity,
        start,
        ...(contract ? { contract: contract.id, unit: contract.unit } : {}),
      });
      if (sequence !== requestNumber || step !== 1) return;
      capacity = result;
      status.className = `alert ${result.globalOkay && result.productOkay ? "alert-success" : "alert-warning"}`;
      status.textContent =
        result.globalOkay && result.productOkay
          ? "Produkt- und Gesamtkapazität sind verfügbar. Abholorte wurden ebenfalls geprüft."
          : "Für diese Menge ist nicht genügend Produkt- oder Gesamtkapazität verfügbar. Bitte Menge oder Produkt ändern.";
      const select = document.getElementById("ac-location");
      if (select) {
        select.innerHTML =
          '<option value="">Bitte Abholort wählen</option>' +
          result.locations
            .map((l) => `<option value="${esc(l.id)}">${esc(l.name)}</option>`)
            .join("");
        select.value = data.location || "";
      }
      if (
        member.location &&
        !result.locations.some((l) => l.id === member.location.id)
      ) {
        status.className = "alert alert-warning";
        status.textContent = `Am hinterlegten Abholort „${member.location.name}“ reicht die Kapazität für diese Auswahl nicht aus.`;
      }
      updateNext();
    } catch (e) {
      if (sequence === requestNumber && step === 1) {
        status.className = "alert alert-danger";
        status.textContent = e.message;
      }
    }
  }
  function details(reset = false) {
    step = 1;
    frame();
    if (reset)
      data = {
        product: contract?.productId || config.products[0]?.id,
        quantity: contract?.quantity || 1,
        startMode: "next",
        rhythm: "",
        location: "",
      };
    const selected = config.products.find((p) => p.id === data.product);
    const types = [
      ...new Map(config.products.map((p) => [p.type_id, p.type__name])),
    ];
    const nextPeriod = config.periods.find((p) => p.start > config.today);
    const weeks = availableWeeks();
    const years = [...new Set(weeks.map((w) => w.year))];
    data.weekYear = data.weekYear || data.week?.slice(0, 4) || "";
    body.innerHTML =
      memberSummary() +
      (flow === "new"
        ? `<details class="mb-3 border rounded p-3"><summary>Vorhandene Anteile (${member.contracts.length}) ansehen</summary><ul class="small mt-2 mb-0">${member.contracts.map((c) => `<li>${esc(c.type)} · ${esc(c.product)} · ${date(c.start)} – ${date(c.end)}${c.cancelled ? " · Gekündigt" : c.ended ? " · Beendet" : ""}</li>`).join("") || "<li>Noch keine Produktverträge vorhanden.</li>"}</ul></details>`
        : "") +
      `<div class="row g-4"><div class="col-md-8"><section class="ac-section"><h5>${contract ? "Bestehenden Vertrag ändern" : "Neuen Vertrag hinzufügen"}</h5>${contract ? `<div class="alert alert-light border small">Bisher: ${esc(contract.product)} · ${date(contract.start)} – ${date(contract.end)}. Du änderst diesen einzelnen Anteil. Wähle die neue Produktanteilsgröße.</div>` : ""}<div class="row g-3"><div class="col-12"><label class="form-label" for="ac-type">Vertragsart</label><select id="ac-type" class="form-select" ${contract ? "disabled" : ""}>${types.map(([id, name]) => `<option value="${esc(id)}" ${id === selected?.type_id ? "selected" : ""}>${esc(name)}</option>`).join("")}</select></div><div class="${contract ? "col-12" : "col-sm-8"}"><label class="form-label" for="ac-product">${contract ? "Produktanteilsgröße" : "Produkt / Variante"}</label><select id="ac-product" class="form-select">${config.products
        .filter((p) => p.type_id === selected?.type_id)
        .map(
          (p) =>
            `<option value="${esc(p.id)}" ${p.id === data.product ? "selected" : ""}>${esc(p.name)}</option>`,
        )
        .join(
          "",
        )}</select></div>${contract ? "" : `<div class="col-sm-4"><label class="form-label" for="ac-quantity">Menge</label><input id="ac-quantity" type="number" min="1" max="32767" step="1" class="form-control" value="${esc(data.quantity)}"></div>`}</div></section><section class="ac-section"><h5>Ab wann soll ${contract ? "die Änderung" : "der Vertrag"} gelten?</h5>${[
        [
          "next",
          "Nächstmöglicher Vertragsbeginn",
          date(config.nextStart) + " · gemäß globaler Konfiguration",
        ],
        [
          "week",
          "Zu einer bestimmten Kalenderwoche in der aktuellen Vertragsperiode",
          "Wähle zuerst das Jahr und danach die Kalenderwoche. Der Vertrag beginnt am Montag dieser Woche.",
        ],
        [
          "period",
          "Beginn der nächsten Vertragsperiode",
          nextPeriod
            ? date(nextPeriod.start)
            : "Keine nächste Vertragsperiode konfiguriert",
        ],
      ]
        .map(
          ([value, title, help]) =>
            `<div class="ac-contract"><label class="d-block" for="ac-start-${value}"><input id="ac-start-${value}" type="radio" class="form-check-input me-2" name="ac-start" value="${value}" ${data.startMode === value ? "checked" : ""} ${value === "period" && !nextPeriod ? "disabled" : ""}><strong>${title}</strong><span class="d-block small text-muted ms-4">${help}</span></label>${value === "week" ? `<div id="ac-week-wrap" class="ms-4 mt-3" ${data.startMode !== "week" ? "hidden" : ""}><div class="row g-3"><div class="col-sm-4"><label class="form-label" for="ac-week-year">1. Jahr</label><select id="ac-week-year" class="form-select"><option value="">Jahr wählen …</option>${years.map((year) => `<option value="${year}" ${data.weekYear === year ? "selected" : ""}>${year}</option>`).join("")}</select></div><div class="col-sm-8"><label class="form-label" for="ac-week">2. Kalenderwoche</label><select id="ac-week" class="form-select" aria-describedby="ac-week-error" ${!data.weekYear ? "disabled" : ""}>${weekOptions(weeks, data.weekYear)}</select><div id="ac-week-error" class="invalid-feedback">Bitte eine aktuelle oder zukünftige Kalenderwoche wählen.</div></div></div>${weeks.length ? '<div class="form-text mt-2">Es werden nur Wochen mit einem noch nicht vergangenen Montag innerhalb der aktuellen Vertragsperiode angeboten.</div>' : '<div class="text-warning small mt-2">In der aktuellen Vertragsperiode ist keine zukünftige Kalenderwoche mehr verfügbar. Bitte eine andere Startoption wählen.</div>'}<div class="small text-muted mt-2" id="ac-effective-date"></div></div>` : ""}</div>`,
        )
        .join(
          "",
        )}</section><div id="ac-capacity" role="status"></div></div><aside class="col-md-4 ac-context"><h5>Abholung &amp; Zahlung</h5><div class="mb-4"><label class="form-label d-flex align-items-center gap-2" for="ac-location">${statusIcon(Boolean(member.location))}Abholort</label>${member.location ? `<div>${esc(member.location.name)}</div><div class="form-text">Für dieses Mitglied hinterlegt. Verfügbarkeit wird für den gewählten Beginn geprüft.</div>` : '<select class="form-select" id="ac-location"><option value="">Kapazitäten werden geladen …</option></select><div class="form-text">Nur Abholorte mit ausreichender Kapazität sind wählbar.</div>'}</div><div class="mb-4"><label class="form-label d-flex align-items-center gap-2" for="ac-rhythm">${statusIcon(Boolean(member.rhythm))}Zahlungsintervall</label>${member.rhythm ? `<div>${esc(member.rhythm)}</div><div class="form-text">Bereits hinterlegt.</div>` : `<select id="ac-rhythm" class="form-select"><option value="">Bitte wählen</option>${config.rhythms.map(([id, label]) => `<option value="${esc(id)}" ${data.rhythm === id ? "selected" : ""}>${esc(label)}</option>`).join("")}</select>`}</div><div><h6 class="d-flex align-items-center gap-2">${statusIcon(member.bankPresent)}Bankverbindung</h6>${member.bankPresent ? '<div class="text-success">Bankdaten vorhanden</div><div class="form-text">Bestehende Bankdaten werden übernommen.</div>' : `<div class="small text-muted mb-2">Bankdaten fehlen. Eingaben bleiben ausschließlich in dieser Vorschau.</div><label for="ac-owner" class="form-label">Kontoinhaber*in</label><input id="ac-owner" class="form-control mb-3" autocomplete="off" value="${esc(data.owner || "")}"><label for="ac-iban" class="form-label">IBAN</label><input id="ac-iban" class="form-control" autocomplete="off" value="${esc(data.iban || "")}"><div class="form-text">Die IBAN wird auf eine gültige Prüfziffer geprüft.</div>`}</div></aside></div>`;
    document.getElementById("ac-type").onchange = (e) => {
      data.product = config.products.find(
        (p) => p.type_id === e.target.value,
      ).id;
      details();
    };
    document.getElementById("ac-product").onchange = (e) => {
      data.product = e.target.value;
      check();
    };
    const quantityInput = document.getElementById("ac-quantity");
    if (quantityInput)
      quantityInput.oninput = (e) => {
        data.quantity = e.target.value;
        check();
      };
    body.querySelectorAll('[name="ac-start"]').forEach(
      (input) =>
        (input.onchange = () => {
          data.startMode = input.value;
          document.getElementById("ac-week-wrap").hidden =
            input.value !== "week";
          check();
        }),
    );
    document.getElementById("ac-week-year").onchange = (e) => {
      data.weekYear = e.target.value;
      data.week = "";
      const weekSelect = document.getElementById("ac-week");
      weekSelect.innerHTML = weekOptions(weeks, data.weekYear);
      weekSelect.disabled = !data.weekYear;
      check();
    };
    document.getElementById("ac-week").onchange = (e) => {
      data.week = e.target.value;
      check();
    };
    for (const [id, key] of [
      ["ac-location", "location"],
      ["ac-rhythm", "rhythm"],
      ["ac-owner", "owner"],
      ["ac-iban", "iban"],
    ]) {
      const field = document.getElementById(id);
      if (field)
        field.oninput = () => {
          data[key] = field.value;
          updateNext();
        };
    }
    check();
  }
  function review() {
    step = 2;
    frame();
    const product = config.products.find((p) => p.id === data.product);
    const location =
      member.location?.name ||
      capacity.locations.find((l) => l.id === data.location)?.name;
    const rhythm =
      member.rhythm || config.rhythms.find(([id]) => id === data.rhythm)?.[1];
    body.innerHTML =
      memberSummary() +
      `<h5 class="mb-4">${contract ? "Vertragsänderung" : "Neuen Vertrag"} prüfen</h5><div class="row g-4"><div class="col-md-7"><div class="card"><div class="card-header">${esc(product.type__name)}</div><div class="card-body"><dl class="row ac-summary mb-0">${[["Aktion", contract ? "Bestehenden Vertrag ändern" : "Zusätzlichen Vertrag hinzufügen"], ...(contract ? [["Bisher", contract.product]] : []), ["Neu", contract ? product.name : `${product.name} × ${data.quantity}`], ["Wirksam ab", date(startDate())], ["Vertragsende", date(capacity.end)], ["Abholort", location], ["Zahlungsintervall", rhythm], ["Bankdaten", member.bankPresent ? "Bereits vorhanden" : "Eingabe für die Vorschau geprüft"]].map(([key, value]) => `<dt class="col-5">${esc(key)}</dt><dd class="col-7">${esc(value)}</dd>`).join("")}</dl></div></div></div><div class="col-md-5"><div class="alert alert-success">Produkt-, Gesamt- und Abholortkapazität wurden über Django geprüft.</div><h6>Vorschau für das Mitgliederprotokoll</h6><div class="border rounded p-3 small">${contract ? "Vertragsänderung" : "Neuer Produktvertrag"}: ${esc(product.type__name)} / ${esc(product.name)} × ${esc(data.quantity)} ab ${date(startDate())}. Erfasst durch die Administration.</div><p class="small text-muted mt-3">Die Speicherung und der Protokolleintrag sind in diesem UI-Prototyp noch nicht implementiert.</p></div></div>`;
    next.disabled = false;
  }
  next.onclick = () => {
    if (step === 0) details(true);
    else if (step === 1) review();
    else {
      bootstrap.Modal.getInstance(modal).hide();
    }
  };
  back.onclick = () => {
    ++requestNumber;
    if (step === 0) bootstrap.Modal.getInstance(modal).hide();
    else if (step === 1) {
      step = 0;
      if (flow === "new") selectMember();
      else showContracts();
    } else details();
  };
  modal.addEventListener("shown.bs.modal", async () => {
    flow = ["new", "change"].includes(modal.dataset.flow)
      ? modal.dataset.flow
      : "combined";
    frame();
    body.textContent = "Testdaten werden geladen …";
    try {
      config = await api({});
      selectMember();
    } catch (e) {
      fail(e.message);
      body.innerHTML = "<p>Bitte den Dialog schließen und erneut öffnen.</p>";
    }
  });
  modal.addEventListener("hidden.bs.modal", () => {
    ++requestNumber;
    ++searchNumber;
    step = 0;
    member = null;
    data = {};
    capacity = null;
  });
})();
