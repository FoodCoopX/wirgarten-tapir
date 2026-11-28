import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import {
  PickupLocationCapacityByShare,
  PickupLocationsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface ProductModalProps {
  show: boolean;
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  pickupLocationId: string;
}

function parseIntOrUndefined(valueAstring: string): number | undefined {
  const value = Number.parseInt(valueAstring);
  if (Number.isNaN(value)) {
    return undefined;
  }
  return value;
}

const PickupLocationCapacityModal: React.FC<ProductModalProps> = ({
  show,
  onHide,
  setToastDatas,
  pickupLocationId,
}) => {
  const api = useApi(PickupLocationsApi);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [locationName, setLocationName] = useState("");
  const [capacitiesByShare, setCapacitiesByShare] = useState<
    PickupLocationCapacityByShare[]
  >([]);

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);

    api
      .pickupLocationsApiPickupLocationCapacitiesRetrieve({
        pickupLocationId: pickupLocationId,
      })
      .then((response) => {
        setLocationName(response.pickupLocationName);
        setCapacitiesByShare(response.capacitiesByShares);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Kapazitäten",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }, [show]);

  function onSave() {
    const form = document.getElementById(
      "pickupLocationCapacityForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setSaving(true);

    api
      .pickupLocationsApiPickupLocationCapacitiesPartialUpdate({
        patchedPickupLocationCapacitiesRequest: {
          pickupLocationId: pickupLocationId,
          pickupLocationName: locationName,
          capacitiesByShares: capacitiesByShare,
        },
      })
      .then(() => location.reload())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Kapazitäten",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function onCapacityByShareChanged(
    productTypeId: string,
    newCapacity: string,
  ) {
    const newCapacities = [...capacitiesByShare];
    for (const capacity of newCapacities) {
      if (capacity.productTypeId === productTypeId) {
        capacity.capacity = parseIntOrUndefined(newCapacity);
        break;
      }
    }
    setCapacitiesByShare(newCapacities);
  }

  function getFromByShare() {
    return (
      <>
        <Form.Text>
          Angaben als Größe im Verhältnis zur Basis-Anteilsgröße. <br />
          0: Kistengröße kann nicht in der Verteilstation geliefert werden.
          <br />
          Feld leer: unbegrenzt.
        </Form.Text>
        {capacitiesByShare.map((capacity) => {
          return (
            <Form.Group key={capacity.productTypeName}>
              <Form.Label>
                Maximale Anzahl ({capacity.productTypeName})
              </Form.Label>
              <Form.Control
                type={"number"}
                value={capacity.capacity ?? ""}
                min={0}
                step={1}
                placeholder={"Unbegrenzt"}
                onChange={(event) => {
                  onCapacityByShareChanged(
                    capacity.productTypeId,
                    event.target.value,
                  );
                }}
              />
            </Form.Group>
          );
        })}
      </>
    );
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <Modal.Body>
        <Form id={"pickupLocationCapacityForm"}>{getFromByShare()}</Form>
      </Modal.Body>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Verteilstation Kapazitäten: {locationName}</h5>
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

export default PickupLocationCapacityModal;
