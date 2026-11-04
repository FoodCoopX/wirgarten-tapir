import { createRoot, type Root } from "react-dom/client";
import TapirHelpButton from "../components/TapirHelpButton.tsx";

// The prototype uses a Django/Bootstrap modal; mount the existing React help
// component into its placeholders and dispose popovers before each step change.
export function installAdminContractPrototypeHelp() {
  const modal = document.getElementById("admin-contract-modal");
  if (!modal) return;
  modal.dispatchEvent(new Event("tapir:prototype-help-dispose"));
  const roots = new Map<HTMLElement, Root>();
  const clear = () => {
    roots.forEach((root) => root.unmount());
    roots.clear();
  };
  const mount = () => {
    modal
      .querySelectorAll<HTMLElement>("[data-admin-contract-help]")
      .forEach((element) => {
        if (roots.has(element)) return;
        const root = createRoot(element);
        roots.set(element, root);
        root.render(
          <TapirHelpButton
            title={element.dataset.helpTitle}
            text={element.dataset.helpText ?? ""}
            buttonSize="sm"
          />,
        );
      });
  };
  modal.addEventListener("tapir:prototype-before-render", clear);
  modal.addEventListener("tapir:prototype-rendered", mount);
  modal.addEventListener("hidden.bs.modal", clear);
  mount();
  modal.addEventListener(
    "tapir:prototype-help-dispose",
    () => {
      clear();
      modal.removeEventListener("tapir:prototype-before-render", clear);
      modal.removeEventListener("tapir:prototype-rendered", mount);
      modal.removeEventListener("hidden.bs.modal", clear);
    },
    { once: true },
  );
}
