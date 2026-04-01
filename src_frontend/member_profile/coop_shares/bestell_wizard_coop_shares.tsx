import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import BestellWizardCoopShares from "./BestellWizardCoopShares.tsx";

const domNode = document.getElementById("bestell_wizard_coop_shares");
if (domNode) {
  const root = createRoot(domNode);

  root.render(
    <BestellWizardCoopShares
      memberId={domNode.dataset.memberId!}
      firstName={domNode.dataset.firstName!}
      lastName={domNode.dataset.lastName!}
      needsBankingData={domNode.dataset.needsBankingData === "True"}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to bestellwizard for coop shares from React");
}
