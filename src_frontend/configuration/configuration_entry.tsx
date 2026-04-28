import { createRoot } from "react-dom/client";
import MandateReferencePreview from "./MandateReferencePreview.tsx";

const configElement = document.getElementById(
  "mandate-reference-preview-config",
);
if (configElement) {
  const parameterKey = configElement.dataset.parameterKey;
  const inputElement = document.getElementById(
    "id_" + parameterKey,
  ) as HTMLInputElement;

  const previewDiv = document.createElement("div");
  inputElement.insertAdjacentElement("afterend", previewDiv);

  const root = createRoot(previewDiv);
  root.render(<MandateReferencePreview inputField={inputElement} />);
} else {
  alert("Failed to render mandate reference preview");
}
