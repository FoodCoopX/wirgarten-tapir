import React from "react";
import { Card, Form } from "react-bootstrap";
import {
  AdminSubscriptionChangePrerequisitesStatus,
  PublicPickupLocation,
} from "../api-client";
import { isIbanValid } from "../bestell_wizard/utils/isIbanValid.ts";
import { SubscriptionPrerequisitesFormData } from "./types/SubscriptionPrerequisitesFormData.ts";
import { isBankingDataComplete } from "./utils/isBankingDataComplete.ts";
import { isPickupLocationComplete } from "./utils/isPickupLocationComplete.ts";

interface MemberSubscriptionPrerequisitesCardProps {
  status: AdminSubscriptionChangePrerequisitesStatus;
  pickupLocations: PublicPickupLocation[];
  formData: SubscriptionPrerequisitesFormData;
  setFormData: (formData: SubscriptionPrerequisitesFormData) => void;
  showValidation: boolean;
}

function StatusIcon({ complete }: { complete: boolean }) {
  return (
    <span
      className={`material-icons fs-6 ${complete ? "text-success" : "text-danger"}`}
    >
      {complete ? "check_circle" : "cancel"}
    </span>
  );
}

const MemberSubscriptionPrerequisitesCard: React.FC<
  MemberSubscriptionPrerequisitesCardProps
> = ({ status, pickupLocations, formData, setFormData, showValidation }) => {
  const pickupLocationComplete = isPickupLocationComplete(status, formData);
  const bankingDataComplete = isBankingDataComplete(status, formData);

  return (
    <Card>
      <Card.Body className={"d-flex flex-column gap-3"}>
        <div>
          <div className={"d-flex flex-row gap-2 align-items-center"}>
            <StatusIcon complete={pickupLocationComplete} />
            <strong>Verteilort</strong>
            {status.pickupLocationName !== null && (
              <span>{status.pickupLocationName}</span>
            )}
          </div>
          {status.pickupLocationName === null && (
            <Form.Select
              className={"mt-2"}
              value={formData.pickupLocationId ?? ""}
              onChange={(event) =>
                setFormData({
                  ...formData,
                  pickupLocationId: event.target.value || undefined,
                })
              }
              isInvalid={showValidation && !formData.pickupLocationId}
            >
              <option value={""}>Verteilort auswählen</option>
              {pickupLocations.map((pickupLocation) => (
                <option key={pickupLocation.id} value={pickupLocation.id}>
                  {pickupLocation.name}
                </option>
              ))}
            </Form.Select>
          )}
        </div>
        <div>
          <div className={"d-flex flex-row gap-2 align-items-center"}>
            <StatusIcon complete={bankingDataComplete} />
            <strong>Bankverbindung</strong>
            {status.hasBankingData && <span>vorhanden</span>}
          </div>
          {!status.hasBankingData && (
            <div className={"d-flex flex-column gap-2 mt-2"}>
              <Form.Control
                value={formData.accountOwner}
                onChange={(event) =>
                  setFormData({ ...formData, accountOwner: event.target.value })
                }
                placeholder={"Kontoinhaber*in"}
                isInvalid={
                  showValidation && formData.accountOwner.trim().length === 0
                }
              />
              <Form.Control
                value={formData.iban}
                onChange={(event) =>
                  setFormData({ ...formData, iban: event.target.value })
                }
                placeholder={"IBAN"}
                isInvalid={showValidation && !isIbanValid(formData.iban)}
              />
              <Form.Check
                id={"sepa_mandate_confirmed"}
                checked={formData.sepaMandateConfirmed}
                onChange={(event) =>
                  setFormData({
                    ...formData,
                    sepaMandateConfirmed: event.target.checked,
                  })
                }
                isInvalid={showValidation && !formData.sepaMandateConfirmed}
                label={"Ein unterschriebenes SEPA-Mandat liegt vor"}
              />
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default MemberSubscriptionPrerequisitesCard;
