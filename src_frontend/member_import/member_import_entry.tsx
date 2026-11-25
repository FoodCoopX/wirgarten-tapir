import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken";
import MemberImportPage from "./MemberImportPage";

const node = document.getElementById("member_import");
if (node) {
  createRoot(node).render(
    <MemberImportPage
      csrfToken={getCsrfToken()}
      templateUrl={node.dataset.templateUrl!}
    />,
  );
}
