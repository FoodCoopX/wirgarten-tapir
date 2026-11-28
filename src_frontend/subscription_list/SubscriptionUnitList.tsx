import React from "react";
import { Badge, ListGroup } from "react-bootstrap";
import {
  AdminSubscriptionChangeSubscriptionUnit,
  AdminSubscriptionChangeSubscriptionUnitStatusEnum,
  PriceCategoryEnum,
} from "../api-client";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { isSubscriptionUnitEditable } from "./utils/isSubscriptionUnitEditable.ts";

const STATUS_LABELS: Record<
  AdminSubscriptionChangeSubscriptionUnitStatusEnum,
  string
> = {
  running: "Laufend",
  planned: "Geplant",
  cancelled: "Gekündigt",
  ended: "Beendet",
};

const PRICE_LABELS: Record<PriceCategoryEnum, string | undefined> = {
  standard: undefined,
  personalised: "Personalisierter Betrag",
  exempt: "Beitragsbefreit",
};

const NOT_EDITABLE_TEXTS: Record<
  AdminSubscriptionChangeSubscriptionUnitStatusEnum,
  string | undefined
> = {
  running: undefined,
  planned: undefined,
  cancelled:
    "Dieser Vertrag ist bereits gekündigt und kann daher nicht bearbeitet werden.",
  ended: "Dieser Vertrag ist beendet und kann daher nicht bearbeitet werden.",
};

interface SubscriptionUnitListProps {
  units: AdminSubscriptionChangeSubscriptionUnit[];
  selectedUnit: AdminSubscriptionChangeSubscriptionUnit | undefined;
  setSelectedUnit: (unit: AdminSubscriptionChangeSubscriptionUnit) => void;
}

const SubscriptionUnitList: React.FC<SubscriptionUnitListProps> = ({
  units,
  selectedUnit,
  setSelectedUnit,
}) => {
  if (units.length === 0) {
    return (
      <span className={"text-muted"}>
        Dieses Mitglied hat keine laufenden oder geplanten Verträge.
      </span>
    );
  }

  return (
    <ListGroup>
      {units.map((unit) => {
        const editable = isSubscriptionUnitEditable(unit);
        const priceLabel = PRICE_LABELS[unit.priceCategory];
        return (
          <ListGroup.Item
            key={`${unit.subscriptionId}_${unit.unitNumber}`}
            action
            disabled={!editable}
            active={
              selectedUnit?.subscriptionId === unit.subscriptionId &&
              selectedUnit.unitNumber === unit.unitNumber
            }
            onClick={() => setSelectedUnit(unit)}
          >
            <div className={"d-flex flex-row gap-2 align-items-center"}>
              <strong>{unit.productName}</strong>
              <Badge bg={editable ? "primary" : "secondary"}>
                {STATUS_LABELS[unit.status]}
              </Badge>
              {priceLabel && (
                <Badge bg={"warning"} text={"dark"}>
                  {priceLabel}
                </Badge>
              )}
            </div>
            <div className={"small"}>
              {formatDateNumeric(unit.startDate)} –{" "}
              {formatDateNumeric(unit.endDate)}
            </div>
            {NOT_EDITABLE_TEXTS[unit.status] && (
              <div className={"small"}>{NOT_EDITABLE_TEXTS[unit.status]}</div>
            )}
          </ListGroup.Item>
        );
      })}
    </ListGroup>
  );
};

export default SubscriptionUnitList;
