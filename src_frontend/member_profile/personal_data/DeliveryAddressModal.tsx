import React, { useEffect, useState } from "react";
import { Alert, Form, Modal, Spinner } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import { DeliveryAddressRequest, PickupLocationsApi } from "../../api-client";
import DeliveryAddressFields from "../../components/DeliveryAddressFields.tsx";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface DeliveryAddressModalProps {
  memberId: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  show: boolean;
  onHide: () => void;
}

const DeliveryAddressModal: React.FC<DeliveryAddressModalProps> = ({
  memberId,
  csrfToken,
  setToastDatas,
  show,
  onHide,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);
  const [form, setForm] = useState<DeliveryAddressRequest>({
    sameAsBillingAddress: true,
  });
  const [changeWarningText, setChangeWarningText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!show) return;

    setLoading(true);
    api
      .pickupLocationsApiMemberDeliveryAddressRetrieve({ memberId: memberId })
      .then((deliveryAddress) => {
        setForm({
          sameAsBillingAddress: deliveryAddress.sameAsBillingAddress,
          street: deliveryAddress.street,
          street2: deliveryAddress.street2,
          postcode: deliveryAddress.postcode,
          city: deliveryAddress.city,
          country: deliveryAddress.country || "DE",
        });
        setChangeWarningText(deliveryAddress.changeWarningText);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Lieferadresse",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onSave() {
    setSaving(true);
    api
      .pickupLocationsApiMemberDeliveryAddressUpdate({
        memberId: memberId,
        deliveryAddressRequest: form,
      })
      .then((response) => {
        if (!response.orderConfirmed) {
          addToast(
            {
              title: "Lieferadresse nicht gespeichert",
              message: response.error ?? undefined,
              variant: "danger",
              id: uuidv4(),
            },
            setToastDatas,
          );
          return;
        }
        onHide();
        globalThis.location.reload();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Speichern der Lieferadresse",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Lieferadresse ändern</h5>
      </Modal.Header>
      <Modal.Body>
        {loading ? (
          <Spinner />
        ) : (
          <Form className={"d-flex flex-column gap-2"}>
            {changeWarningText && (
              <Alert variant={"warning"} className={"mb-0"}>
                <span dangerouslySetInnerHTML={{ __html: changeWarningText }} />
              </Alert>
            )}
            <DeliveryAddressFields
              deliveryAddress={form}
              setDeliveryAddress={setForm}
            />
          </Form>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Speichern"}
          icon={"save"}
          onClick={onSave}
          loading={saving}
          disabled={loading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default DeliveryAddressModal;
