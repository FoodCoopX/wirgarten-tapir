(function () {
    var prefixKey = document.getElementById("member-number-preview-config").dataset.prefixKey;
    var lengthKey = document.getElementById("member-number-preview-config").dataset.lengthKey;
    var previewUrl = document.getElementById("member-number-preview-config").dataset.previewUrl;

    function findFieldByKey(key) {
        var spans = document.querySelectorAll('span[name="param-key"]');
        for (var i = 0; i < spans.length; i++) {
            if (spans[i].textContent.trim() === key) {
                var parameterDiv = spans[i].closest(".single-parameter");
                if (!parameterDiv) return null;
                return parameterDiv.querySelector("input, select, textarea");
            }
        }
        return null;
    }

    var prefixField = findFieldByKey(prefixKey);
    var lengthField = findFieldByKey(lengthKey);

    if (!prefixField || !lengthField) return;

    var previewDiv = document.createElement("div");
    previewDiv.className = "form-text";
    previewDiv.style.marginTop = "0.5rem";
    previewDiv.style.fontWeight = "500";
    prefixField.closest(".single-parameter").appendChild(previewDiv);

    var debounceTimer = null;

    function updatePreview() {
        var prefix = prefixField.value || "";
        var length = parseInt(lengthField.value, 10) || 0;

        var url = previewUrl + "?prefix=" + encodeURIComponent(prefix) + "&length=" + length;
        fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                previewDiv.textContent = "Vorschau: " + data.previews.join(", ");
            });
    }

    function debouncedUpdate() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(updatePreview, 200);
    }

    [prefixField, lengthField].forEach(function (field) {
        field.addEventListener("input", debouncedUpdate);
        field.addEventListener("change", debouncedUpdate);
    });

    updatePreview();
})();
