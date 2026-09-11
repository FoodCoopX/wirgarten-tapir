import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import AssociationMembershipsConfigBase from "./AssociationMembershipsConfigBase.tsx";

const domNode = document.getElementById("association_memberships_config");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<AssociationMembershipsConfigBase csrfToken={getCsrfToken()} />);
} else {
  console.error("Failed to render association membership config from React");
}
