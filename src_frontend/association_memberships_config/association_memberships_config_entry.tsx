import { createRoot } from "react-dom/client";
import AssociationMembershipsConfigBase from "./AssociationMembershipsConfigBase.tsx";

const domNode = document.getElementById("association_memberships_config");
if (domNode) {
  const root = createRoot(domNode);
  root.render(<AssociationMembershipsConfigBase />);
} else {
  console.error("Failed to render association membership config from React");
}
