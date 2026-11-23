import React from "react";
import { Alert } from "react-bootstrap";
import {
  AdminSubscriptionChangeMemberData,
  AdminSubscriptionChangeSubscriptionUnit,
  Product,
} from "../api-client";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { SubscriptionPrerequisitesFormData } from "./types/SubscriptionPrerequisitesFormData.ts";

interface AdminSizeChangeSummaryProps {
  memberData: AdminSubscriptionChangeMemberData;
  unit: AdminSubscriptionChangeSubscriptionUnit;
  newProduct: Product;
  changeDate: string;
  prerequisites: SubscriptionPrerequisitesFormData;
  pickupLocationName: string | undefined;
}

const AdminSizeChangeSummary: React.FC<AdminSizeChangeSummaryProps> = ({
  memberData,
  unit,
  newProduct,
  changeDate,
  prerequisites,
  pickupLocationName,
}) => {
  const unitsOfSameType = memberData.subscriptionUnits.filter(
    (other) => other.productTypeId === unit.productTypeId,
  );
  const hasPriceOverride = unitsOfSameType.some(
    (other) => other.priceCategory !== "standard",
  );
  const hasNextPeriodSubscriptions = unitsOfSameType.some(
    (other) => other.startDate > unit.endDate,
  );

  return (
    <div className={"d-flex flex-column gap-3"}>
      <dl className={"row mb-0"}>
        <dt className={"col-4"}>Mitglied</dt>
        <dd className={"col-8"}>{memberData.member.displayName}</dd>
        <dt className={"col-4"}>Bisher</dt>
        <dd className={"col-8"}>
          {unit.productTypeName} · {unit.productName}
        </dd>
        <dt className={"col-4"}>Neu</dt>
        <dd className={"col-8"}>
          {unit.productTypeName} · {newProduct.name}
        </dd>
        <dt className={"col-4"}>Wirksam ab</dt>
        <dd className={"col-8"}>{formatDateNumeric(changeDate)}</dd>
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
      {hasPriceOverride && (
        <Alert variant={"warning"} className={"mb-0"}>
          Der personalisierte Betrag bzw. die Beitragsbefreiung wird für alle
          Anteile dieses Produktanteils entfernt und muss danach neu gesetzt
          werden.
        </Alert>
      )}
      {hasNextPeriodSubscriptions && (
        <Alert variant={"warning"} className={"mb-0"}>
          Die Verträge dieses Produktanteils in der nächsten Vertragsperiode
          werden durch Verlängerungen der neuen Verträge ersetzt.
        </Alert>
      )}
      <Alert variant={"info"} className={"mb-0"}>
        Das Mitglied erhält die Mail, die für den Trigger „Vertragsänderungen im
        Mitgliederbereich“ hinterlegt ist.
      </Alert>
    </div>
  );
};

export default AdminSizeChangeSummary;
