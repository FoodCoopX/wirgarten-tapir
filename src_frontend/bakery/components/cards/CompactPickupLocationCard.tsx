import React from "react";
import { GeoAlt } from "react-bootstrap-icons";
import TapirButton from "../../../components/TapirButton";
import "../../styles/bakery_styles.css";
import { DAY_LABELS, formatDeliveryDate } from "../../utils/weekdays";

interface CompactPickupLocationCardProps {
  name: string;
  street?: string;
  city?: string;
  deliveryDay?: number;
  onEdit?: () => void;
  disabled?: boolean;
  year?: number;
  week?: number;
}

export const CompactPickupLocationCard: React.FC<
  CompactPickupLocationCardProps
> = ({
  name,
  street,
  city,
  deliveryDay,
  onEdit,
  disabled = false,
  year,
  week,
}) => {
  const deliveryDate =
    year && week && deliveryDay !== undefined && deliveryDay !== null
      ? formatDeliveryDate(year, week, deliveryDay)
      : null;

  return (
    <div className="card w-100 card-bakery-border-left">
      <div className="card-body p-3">
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center mb-2">
              <GeoAlt size={18} className="me-2 icon-bakery-primary-darker" />
              <h6 className="mb-0 text-bakery-primary-darker">{name}</h6>
            </div>

            {street && city && (
              <p
                className="text-muted small mb-1"
                style={{ fontSize: "0.85rem", marginLeft: "26px" }}
              >
                {street}, {city}
              </p>
            )}

            {deliveryDay !== undefined && deliveryDay !== null && (
              <div
                className="d-flex align-items-center text-muted small"
                style={{ marginLeft: "26px" }}
              >
                <span style={{ fontSize: "0.85rem" }}>
                  Lieferung: {DAY_LABELS[deliveryDay] || `Tag ${deliveryDay}`}
                  {deliveryDate && `, ${deliveryDate}`}
                </span>
              </div>
            )}
          </div>

          {onEdit && (
            <TapirButton
              variant=""
              className="dark-brown-button"
              size="sm"
              text="Ändern"
              onClick={onEdit}
              disabled={disabled}
            />
          )}
        </div>
      </div>
    </div>
  );
};
