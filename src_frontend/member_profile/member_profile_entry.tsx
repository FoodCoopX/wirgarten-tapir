import { createRoot } from "react-dom/client";
import DeliveryListCard from "./deliveries_and_jokers/DeliveryListCard.tsx";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import SubscriptionCancellationCard from "./subscription_cancellation/SubscriptionCancellationCard.tsx";
import SubscriptionCards from "./subscriptions/SubscriptionCards.tsx";
import MemberProfileWaitingListCard from "./waiting_list/MemberProfileWaitingListCard.tsx";
import FuturePaymentsCard from "./future_payments/FuturePaymentsCard.tsx";
import MemberProfilePaymentRhythmBase from "./payment_rhythm/MemberProfilePaymentRhythmBase.tsx";
import CoopSharesCard from "./coop_shares/CoopSharesCard.tsx";
import MemberProfileSolidarityContributionCard from "./solidarity_contribution/MemberProfileSolidarityContributionCard.tsx";
import MemberMailCategoryCard from "./mail_category/MemberMailCategoryCard.tsx";
import MemberExtraEmailsBase from "./extra_email_addresses/MemberExtraEmailsBase.tsx";

const domNodeDeliveryListCard = document.getElementById("delivery_list_card");
if (domNodeDeliveryListCard) {
  const root = createRoot(domNodeDeliveryListCard);

  root.render(
    <DeliveryListCard
      memberId={domNodeDeliveryListCard.dataset.memberId!}
      areJokersEnabled={
        domNodeDeliveryListCard.dataset.jokersEnabled === "true"
      }
      areDonationsEnabled={
        domNodeDeliveryListCard.dataset.donationsEnabled === "true"
      }
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to render delivery list card from React");
}

const contractTilesElement = document.getElementById("contract-tiles");
if (contractTilesElement) {
  const root = createRoot(contractTilesElement);
  const showCancellationCard =
    contractTilesElement.dataset.showCancellationCard === "True";
  root.render(
    <>
      <SubscriptionCards
        memberId={contractTilesElement.dataset.memberId!}
        csrfToken={getCsrfToken()}
      />
      {showCancellationCard && (
        <SubscriptionCancellationCard
          memberId={contractTilesElement.dataset.memberId!}
          csrfToken={getCsrfToken()}
        />
      )}
    </>,
  );
}

const domNodeWaitingListCard = document.getElementById(
  "member_profile_waiting_list_entry",
);
if (domNodeWaitingListCard) {
  const root = createRoot(domNodeWaitingListCard);

  root.render(
    <MemberProfileWaitingListCard
      memberId={domNodeWaitingListCard.dataset.memberId!}
      adminEmail={domNodeWaitingListCard.dataset.adminEmail!}
    />,
  );
} else {
  console.error("Failed to render waiting list card from React");
}

const domNodeSolidarityCard = document.getElementById(
  "member_profile_solidarity_contribution",
);
if (domNodeSolidarityCard) {
  const root = createRoot(domNodeSolidarityCard);

  root.render(
    <MemberProfileSolidarityContributionCard
      memberId={domNodeSolidarityCard.dataset.memberId!}
      adminEmail={domNodeSolidarityCard.dataset.adminEmail!}
    />,
  );
} else {
  console.error("Failed to render solidarity card from React");
}

const domNodeFuturePaymentsCard = document.getElementById(
  "future_payments_card",
);
if (domNodeFuturePaymentsCard) {
  const root = createRoot(domNodeFuturePaymentsCard);

  root.render(
    <FuturePaymentsCard
      memberId={domNodeFuturePaymentsCard.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to render future payments card from React");
}

const domNodePaymentRhythmButton = document.getElementById(
  "payment_rhythm_button",
);
if (domNodePaymentRhythmButton) {
  const root = createRoot(domNodePaymentRhythmButton);

  root.render(
    <MemberProfilePaymentRhythmBase
      memberId={domNodePaymentRhythmButton.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
} else {
  console.error("Failed to render payment rhythm button from React");
}

const domNodeCoopSharesCard = document.getElementById("coop_shares_card");
if (domNodeCoopSharesCard) {
  const root = createRoot(domNodeCoopSharesCard);

  root.render(
    <CoopSharesCard
      memberId={domNodeCoopSharesCard.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
}

const domNodeMemberMailCategory = document.getElementById(
  "member_mail_category",
);
if (domNodeMemberMailCategory) {
  const root = createRoot(domNodeMemberMailCategory);

  root.render(
    <MemberMailCategoryCard
      memberId={domNodeMemberMailCategory.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
}

const domNodeMemberExtraAddresses = document.getElementById(
  "extra_email_addresses",
);
if (domNodeMemberExtraAddresses) {
  const root = createRoot(domNodeMemberExtraAddresses);

  root.render(
    <MemberExtraEmailsBase
      memberId={domNodeMemberExtraAddresses.dataset.memberId!}
      csrfToken={getCsrfToken()}
    />,
  );
}
