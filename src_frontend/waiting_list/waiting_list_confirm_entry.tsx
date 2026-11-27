import { createRoot } from "react-dom/client";
import WaitingListConfirmBase from "./WaitingListConfirmBase.tsx";

const domNode = document.getElementById("waiting_list_confirm");
if (domNode) {
  const root = createRoot(domNode);
  root.render(
    <WaitingListConfirmBase
      waitingListEntryId={domNode.dataset.entryId ?? ""}
      waitingListLinkKey={domNode.dataset.linkKey ?? ""}
      adminEmail={domNode.dataset.adminEmail ?? ""}
    />,
  );
} else {
  console.error("Failed to render bestell wizard from React");
}
