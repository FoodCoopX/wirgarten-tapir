import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
import { PickupLocationsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import { getParameterFromUrl } from "../product_config/get_parameter_from_url.ts";

interface ProductModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
}

const PickupLocationCapacityModal: React.FC<ProductModalProps> = ({
  show,
  onHide,
  csrfToken,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [locationName, setLocationName] = useState("");

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
      })
      .catch(alert)
      .finally(() => setDataLoading(false));
  }, [show]);

  function onSave() {
    setSaving(true);

    alert("TODO save");
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return <Modal.Body>COUCOU</Modal.Body>;
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
