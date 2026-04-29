import { createRoot } from "react-dom/client";
import IntendedUseEditorBase from "./payment_intended_use/IntendedUseEditorBase.tsx";

const configElement = document.getElementById("payment-intended-use-config");

if (configElement) {
  const contractKeys = configElement.dataset.contractKeys?.split(",") ?? [];
  for (const parameterKey of contractKeys) {
    console.log(parameterKey);
    createEditorRoot(parameterKey);
  }
} else {
  alert("Failed to render payment intended use editor");
}

function createEditorRoot(parameterKey: string) {
  const inputElement = document.getElementById(
    "id_" + parameterKey,
  ) as HTMLInputElement;

  const previewDiv = document.createElement("div");

  const container = document.createElement("div");
  container.className = "d-flex flex-row gap-2";
  inputElement.parentNode?.insertBefore(container, inputElement);
  container.appendChild(inputElement);
  container.append(previewDiv);

  inputElement.insertAdjacentElement("afterend", previewDiv);

  const root = createRoot(previewDiv);
  root.render(
    <IntendedUseEditorBase
      inputField={inputElement}
      isContract={true}
      parameterKey={parameterKey}
    />,
  );
}
