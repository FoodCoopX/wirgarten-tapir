import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import BestellWizardAssociationMembership from "./BestellWizardAssociationMembership.tsx";

const domNode = document.getElementById(
  "bestell_wizard_association_membership",
);
if (domNode) {
  const root = createRoot(domNode);

  root.render(
    <BestellWizardAssociationMembership
      memberId={domNode.dataset.memberId!}
      firstName={domNode.dataset.firstName!}
      lastName={domNode.dataset.lastName!}
      needsBankingData={domNode.dataset.needsBankingData === "True"}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error(
    "Failed to bestellwizard for association membership from React",
  );
}
