import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import {
  PickupLocationCapacityByShare,
  PickupLocationsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";

interface ProductModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const PickupLocationCapacityModal: React.FC<ProductModalProps> = ({
  show,
  onHide,
  csrfToken,
  setToastDatas,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [locationName, setLocationName] = useState("");
  const [capacitiesByShare, setCapacitiesByShare] = useState<
    PickupLocationCapacityByShare[]
  >([]);

  const URL_PARAMETER_PICKUP_LOCATION_ID = "selected";

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);

    const pickupLocationId = getParameterFromUrl(
      URL_PARAMETER_PICKUP_LOCATION_ID,
    );
    if (!pickupLocationId) return;

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
          pickupLocationId: getParameterFromUrl(
            URL_PARAMETER_PICKUP_LOCATION_ID,
          ),
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

  function parseIntOrUndefined(valueAstring: string): number | undefined {
    const value = parseInt(valueAstring);
    if (isNaN(value)) {
      return undefined;
    }
    return value;
  }

  function getFromByShare() {
    return (
      <>
        <Form.Text>
          Angaben in Anteilsgröße (M-Anteil-Equivalent). <br />
          0: Kistengröße kann nicht in der Verteilstation geliefert werden.
          <br />
          Feld leer: unbegrenzt.
        </Form.Text>
        {capacitiesByShare.map((capacity) => {
          return (
            <Form.Group key={capacity.productTypeName}>
              <Form.Label>
                Maximum Anzahl an {capacity.productTypeName}
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
