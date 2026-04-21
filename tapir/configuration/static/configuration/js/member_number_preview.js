(function () {
    const configEl = document.getElementById("member-number-preview-config");
    const prefixKey = configEl.dataset.prefixKey;
    const lengthKey = configEl.dataset.lengthKey;
    const previewUrl = configEl.dataset.previewUrl;

    const prefixField = document.getElementById("id_" + prefixKey);
    const lengthField = document.getElementById("id_" + lengthKey);

    if (!prefixField || !lengthField) {
        const container = configEl.parentElement;
        const errorDiv = document.createElement("div");
        errorDiv.className = "alert alert-warning";
        errorDiv.textContent = "Vorschau nicht verfügbar: Felder nicht gefunden.";
        container.appendChild(errorDiv);
        return;
    }

    const previewDiv = document.createElement("div");
    previewDiv.className = "form-text";
    previewDiv.style.marginTop = "0.5rem";
    previewDiv.style.fontWeight = "500";
    prefixField.closest(".single-parameter").appendChild(previewDiv);

    let debounceTimer = null;

    function updatePreview() {
        const prefix = prefixField.value || "";
        const length = Number.parseInt(lengthField.value, 10) || 0;

        const url = previewUrl + "?prefix=" + encodeURIComponent(prefix) + "&length=" + length;
        fetch(url)
            .then(function (response) {
                if (!response.ok) {
                    return response.json().then(function (data) {
                        throw new Error(data.error || "Unbekannter Fehler");
                    });
                }
                return response.json();
            })
            .then(function (data) {
                previewDiv.textContent = "Vorschau: " + data.previews.join(", ");
                previewDiv.className = "form-text";
            })
            .catch(function (err) {
                previewDiv.textContent = "Vorschau nicht verfügbar: " + err.message;
                previewDiv.className = "form-text text-danger";
            });
    }

    function debouncedUpdate() {
        clearTimeout(debounceTimer);
        // Debounce: wait 200ms after last keystroke before calling the API
        debounceTimer = setTimeout(updatePreview, 200);
    }

    for (const field of [prefixField, lengthField]) {
        field.addEventListener("input", debouncedUpdate);
        field.addEventListener("change", debouncedUpdate);
    }

    updatePreview();
})();
