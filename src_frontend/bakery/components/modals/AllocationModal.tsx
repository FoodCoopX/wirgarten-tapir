import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import { ExclamationTriangle, InfoCircle } from "react-bootstrap-icons";
import { BakeryApi } from "../../../api-client";
import type {
  BreadList,
  PickupLocationDeliveryDay,
} from "../../../api-client/models";
import TapirButton from "../../../components/TapirButton";
import { useApi } from "../../../hooks/useApi";
import { handleRequestError } from "../../../utils/handleRequestError";
import "../../styles/bakery_styles.css";
import type { AllocationData } from "./AllocationTable";
import { AllocationTable } from "./AllocationTable";

interface AllocationModalProps {
  isOpen: boolean;
  onClose: () => void;
  year: number;
  week: number;
  day: number;
  dayLabel: string;
  activeBreads: BreadList[];
  csrfToken: string;
}

export const AllocationModal: React.FC<AllocationModalProps> = ({
  isOpen,
  onClose,
  year,
  week,
  day,
  dayLabel,
  activeBreads,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [pickupLocations, setPickupLocations] = useState<
    PickupLocationDeliveryDay[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [allocations, setAllocations] = useState<AllocationData>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, year, week, day]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !saving) {
      e.preventDefault();
      handleSaveAndClose();
    }
  };

  const loadData = () => {
    setLoading(true);

    bakeryApi
      .pickupLocationsApiPickupLocationsByDeliveryDayRetrieve({
        dayOfWeek: day,
      })
      .then((locationsResponse) => {
        setPickupLocations(locationsResponse.pickupLocations);

        const locationIds = locationsResponse.pickupLocations.map((s) => s.id);

        return bakeryApi
          .bakeryBreadCapacityPickupLocationList({
            year,
            week,
            pickupLocationIds: locationIds,
          })
          .then((capacities) => {
            const initial: AllocationData = {};
            locationsResponse.pickupLocations.forEach((location) => {
              initial[location.id] = {};
            });
            capacities.forEach((capacity) => {
              initial[capacity.pickupLocation][capacity.bread] =
                capacity.capacity;
            });

            setAllocations(initial);
          });
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Laden der Daten");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleCellChange = (
    pickupLocationId: string,
    breadId: string,
    value: number | null,
  ) => {
    setAllocations((prev) => ({
      ...prev,
      [pickupLocationId]: {
        ...prev[pickupLocationId],
        [breadId]: value,
      },
    }));
  };

  const handleSaveAndClose = () => {
    setSaving(true);

    const updates: Array<{
      pickupLocation: string;
      bread: string;
      capacity: number | null;
    }> = [];

    Object.entries(allocations).forEach(([pickupLocationId, breadAllocs]) => {
      Object.entries(breadAllocs).forEach(([breadId, value]) => {
        updates.push({
          pickupLocation: pickupLocationId,
          bread: breadId,
          capacity: value,
        });
      });
    });

    bakeryApi
      .bakeryBreadCapacityPickupLocationBulkUpdateCreate({
        breadCapacityBulkUpdateRequest: {
          year,
          deliveryWeek: week,
          updates,
        },
      })
      .then(() => {
        onClose();
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Speichern der Mengen");
      })
      .finally(() => {
        setSaving(false);
      });
  };

  const getModalSize = (): "lg" | "xl" | undefined => {
    const count = activeBreads.length;
    if (count <= 2) return "lg";
    if (count <= 4) return "xl";
    return undefined;
  };

  const renderModalBodyContent = () => {
    if (loading) {
      return (
        <div className="text-center py-5">
          <div className="spinner-border spinner-bakery-primary" />
          <p className="mt-2 text-muted">Lade Daten...</p>
        </div>
      );
    }

    if (activeBreads.length === 0) {
      return (
        <div
          className="alert alert-info d-flex align-items-center"
          role="alert"
        >
          <InfoCircle size={20} className="me-2" />
          Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im
          Wochenplan.
        </div>
      );
    }

    if (pickupLocations.length === 0) {
      return (
        <div
          className="alert alert-warning d-flex align-items-center"
          role="alert"
        >
          <ExclamationTriangle size={20} className="me-2" />
          Keine Abholorte für {dayLabel} konfiguriert.
        </div>
      );
    }

    return (
      <AllocationTable
        activeBreads={activeBreads}
        pickupLocations={pickupLocations}
        allocations={allocations}
        onCellChange={handleCellChange}
      />
    );
  };

  return (
    <Modal
      show={isOpen}
      onHide={onClose}
      size={activeBreads.length > 4 ? undefined : getModalSize()}
      fullscreen={activeBreads.length > 4 || undefined}
      centered
      scrollable
      onKeyDown={handleKeyDown}
    >
      <Modal.Header closeButton className="header-white-on-middle-brown">
        <Modal.Title>
          <h5 className="mb-0">
            Mengen zuweisen - {dayLabel}, KW {week}/{year}
          </h5>
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="p-3">{renderModalBodyContent()}</Modal.Body>

      <Modal.Footer>
        <TapirButton
          variant="secondary"
          text="Abbrechen"
          icon="close"
          onClick={onClose}
          disabled={saving}
          size="sm"
        />
        <TapirButton
          variant=""
          className="dark-brown-button"
          text="Speichern & Schließen"
          icon="save"
          onClick={handleSaveAndClose}
          disabled={saving}
          loading={saving}
          size="sm"
        />
      </Modal.Footer>
    </Modal>
  );
};
