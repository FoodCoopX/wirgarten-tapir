import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import {
  GrowingPeriod,
  GrowingPeriodEntry,
  PickupLocationsApi,
} from "../api-client";
import { DeliveriesApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface PickupLocationGrowingPeriodModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  pickupLocationId: string;
}

const PickupLocationGrowingPeriodModal: React.FC<
  PickupLocationGrowingPeriodModalProps
> = ({ show, onHide, csrfToken, setToastDatas, pickupLocationId }) => {
  const api = useApi(PickupLocationsApi, csrfToken);
  const deliveriesApi = useApi(DeliveriesApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [allGrowingPeriods, setAllGrowingPeriods] = useState<GrowingPeriod[]>([]);
  const [selectedGrowingPeriodIds, setSelectedGrowingPeriodIds] = useState<
    Set<string>
  >(new Set());

  function loadData() {
    setDataLoading(true);
    Promise.all([
      api.pickupLocationsPickupLocationGrowingPeriodsList({
        pickupLocationId: pickupLocationId,
      }),
      deliveriesApi.deliveriesGrowingPeriodsList(),
    ])
      .then(([assignedList, all]) => {
        const assigned = assignedList[0];
        const assignedEntries: GrowingPeriodEntry[] = assigned?.growingPeriods ?? [];
        setAllGrowingPeriods(all);
        setSelectedGrowingPeriodIds(
          new Set(assignedEntries.map((gp) => gp.id)),
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsperioden",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  useEffect(() => {
    if (!show) return;
    loadData();
  }, [show]);

  function toggleGrowingPeriod(growingPeriodId: string, checked: boolean) {
    const newSet = new Set(selectedGrowingPeriodIds);
    if (checked) {
      newSet.add(growingPeriodId);
    } else {
      newSet.delete(growingPeriodId);
    }
    setSelectedGrowingPeriodIds(newSet);
  }

  function onSave() {
    setSaving(true);
    api
      .pickupLocationsPickupLocationGrowingPeriodsCreate({
        pickupLocationGrowingPeriodSetRequestRequest: {
          pickupLocationId: pickupLocationId,
          growingPeriodIds: Array.from(selectedGrowingPeriodIds),
        },
      })
      .then(() => location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Vertragsperioden",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    if (allGrowingPeriods.length === 0) {
      return (
        <Modal.Body>
          <span>Keine Vertragsperioden vorhanden.</span>
        </Modal.Body>
      );
    }

    return (
      <Modal.Body>
        <Form>
          {allGrowingPeriods.map((gp) => (
            <Form.Check
              key={gp.id}
              type={"checkbox"}
              id={`growing-period-${gp.id}`}
              label={`${gp.startDate.toLocaleDateString("de-DE")} – ${gp.endDate.toLocaleDateString("de-DE")}`}
              checked={selectedGrowingPeriodIds.has(gp.id!)}
              onChange={(event) =>
                toggleGrowingPeriod(gp.id!, event.target.checked)
              }
            />
          ))}
        </Form>
        <div className={"text-muted small mt-3"}>
          Wähle die Vertragsperioden, in denen dieser Abholort angeboten werden
          soll. Wenn das Feature deaktiviert ist, hat diese Auswahl keine
          Auswirkung.
        </div>
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Vertragsperioden zuordnen</h5>
      </Modal.Header>
      {getModalBody()}
      <Modal.Footer>
        <TapirButton
          text={"Speichern"}
          icon={"save"}
          variant={"primary"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default PickupLocationGrowingPeriodModal;