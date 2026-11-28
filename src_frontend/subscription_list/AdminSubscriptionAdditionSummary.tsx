import React from "react";
import { Alert } from "react-bootstrap";
import { AdminSubscriptionChangeMemberData, Product } from "../api-client";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { SubscriptionPrerequisitesFormData } from "./types/SubscriptionPrerequisitesFormData.ts";

interface AdminSubscriptionAdditionSummaryProps {
  memberData: AdminSubscriptionChangeMemberData;
  product: Product;
  quantity: number;
  startDate: string;
  prerequisites: SubscriptionPrerequisitesFormData;
  pickupLocationName: string | undefined;
}

const AdminSubscriptionAdditionSummary: React.FC<
  AdminSubscriptionAdditionSummaryProps
> = ({
  memberData,
  product,
  quantity,
  startDate,
  prerequisites,
  pickupLocationName,
}) => {
  return (
    <div className={"d-flex flex-column gap-3"}>
      <dl className={"row mb-0"}>
        <dt className={"col-4"}>Mitglied</dt>
        <dd className={"col-8"}>{memberData.member.displayName}</dd>
        <dt className={"col-4"}>Neuer Vertrag</dt>
        <dd className={"col-8"}>
          {quantity} × {product.name}
        </dd>
        <dt className={"col-4"}>Vertragsbeginn</dt>
        <dd className={"col-8"}>{formatDateNumeric(startDate)}</dd>
        <dt className={"col-4"}>Abholort</dt>
        <dd className={"col-8"}>{pickupLocationName}</dd>
        <dt className={"col-4"}>Zahlungsintervall</dt>
        <dd className={"col-8"}>{memberData.paymentRhythmLabel}</dd>
        <dt className={"col-4"}>Bankverbindung</dt>
        <dd className={"col-8"}>
          {memberData.prerequisites.hasBankingData
            ? "vorhanden"
            : `${prerequisites.accountOwner}, ${prerequisites.iban}`}
        </dd>
      </dl>
      <Alert variant={"info"} className={"mb-0"}>
        Das Mitglied erhält die Mail, die für den Trigger „Vertragsänderungen im
        Mitgliederbereich“ hinterlegt ist.
      </Alert>
    </div>
  );
};

export default AdminSubscriptionAdditionSummary;
