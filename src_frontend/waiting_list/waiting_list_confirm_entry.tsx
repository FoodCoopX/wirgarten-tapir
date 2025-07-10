import { createRoot } from "react-dom/client";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import WaitingListConfirmBase from "./WaitingListConfirmBase.tsx";

const domNode = document.getElementById("waiting_list_confirm");
if (domNode) {
  const root = createRoot(domNode);
  root.render(
    <WaitingListConfirmBase
      csrfToken={getCsrfToken()}
      waitingListEntryId={domNode.dataset.entryId ?? ""}
      waitingListLinkKey={domNode.dataset.linkKey ?? ""}
    />,
  );
} else {
  console.error("Failed to render bestell wizard from React");
}
