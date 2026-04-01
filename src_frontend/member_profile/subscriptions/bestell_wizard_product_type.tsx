import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import BestellWizardProductType from "./BestellWizardProductType.tsx";

const domNode = document.getElementById("bestell_wizard_product_type");
if (domNode) {
  const root = createRoot(domNode);

  root.render(
    <BestellWizardProductType
      memberId={domNode.dataset.memberId!}
      firstName={domNode.dataset.firstName!}
      lastName={domNode.dataset.lastName!}
      needsBankingData={domNode.dataset.needsBankingData === "True"}
      productTypeId={domNode.dataset.productTypeId!}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to bestellwizard for coop shares from React");
}
