import { createRoot } from "react-dom/client";
import IntendedUseEditorBase from "./payment_intended_use/IntendedUseEditorBase.tsx";

const configElement = document.getElementById("payment-intended-use-config");

if (configElement) {
  const contractKeys = configElement.dataset.contractKeys?.split(",") ?? [];
  for (const parameterKey of contractKeys) {
    createEditorRoot(parameterKey, true);
  }

  const coopKeys = configElement.dataset.coopSharesKeys?.split(",") ?? [];
  for (const parameterKey of coopKeys) {
    createEditorRoot(parameterKey, false);
  }
} else {
  alert("Failed to render payment intended use editor");
}

function createEditorRoot(parameterKey: string, isContract: boolean) {
  const inputElement = document.getElementById(
    "id_" + parameterKey,
  ) as HTMLTextAreaElement;

  const previewDiv = document.createElement("div");

  const container = document.createElement("div");
  container.className = "d-flex flex-row gap-2";
  inputElement.parentNode?.insertBefore(container, inputElement);
  container.appendChild(inputElement);
  container.append(previewDiv);

  inputElement.after(previewDiv);

  const root = createRoot(previewDiv);
  root.render(
    <IntendedUseEditorBase
      inputField={inputElement}
      isContract={isContract}
      title={inputElement.labels[0].innerText}
    />,
  );
}
