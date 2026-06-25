import React, { useEffect, useState } from "react";
import { Alert, Form, Modal, Table } from "react-bootstrap";
import {
  AssociationMembershipType,
  AssociationMembershipTypePrice,
  AssociationsApi,
} from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface AssociationMembershipTypePriceModalProps {
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  onEdited: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  membershipType: AssociationMembershipType;
}

const AssociationMembershipTypePriceModal: React.FC<
  AssociationMembershipTypePriceModalProps
> = ({ csrfToken, onEdited, onHide, show, setToastDatas, membershipType }) => {
  const api = useApi(AssociationsApi, csrfToken);
  const [saving, setSaving] = useState(false);
  const [addPriceDate, setAddPriceDate] = useState("");
  const [addPriceAmount, setAddPriceAmount] = useState("");
  const [error, setError] = useState("");
  const [priceSelectedForDeletion, setPriceSelectedForDeletion] =
    useState<AssociationMembershipTypePrice>();

  useEffect(() => {
    setError("");
  }, [addPriceDate, addPriceAmount]);

  function onAddPrice() {
    const validFrom = new Date(addPriceDate);
    if (Number.isNaN(validFrom.valueOf())) {
      setError("Ungültiges Datum");
      return;
    }

    const price = Number.parseFloat(addPriceAmount);
    if (Number.isNaN(price)) {
      setError("Ungültiger Preis");
      return;
    }

    setSaving(true);

    api
      .associationsAssociationMembershipTypesPriceCreate({
        associationMembershipTypePriceRequest: {
          type: membershipType.id!,
          price: price.toFixed(2),
          validFrom: validFrom,
        },
      })
      .then(onEdited)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim hinzufügen einen Mitgliedschafttyp-Preis",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  function onDelete() {
    setSaving(true);

    api
      .associationsAssociationMembershipTypesPriceDestroy({
        id: priceSelectedForDeletion!.id!,
      })
      .then(onEdited)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen einen Mitgliedschafttyp-Preis",
          setToastDatas,
        ),
      )
      .finally(() => setSaving(false));
  }

  return (
    <>
      <Modal
        show={show && priceSelectedForDeletion === undefined}
        onHide={onHide}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton={true}>
          <div
            className={"d-flex justify-content-between align-items-center"}
            style={{ width: "100%" }}
          >
            <Modal.Title>
              Preise des Mitgliedschafttyps {membershipType.name}
            </Modal.Title>
            <TapirHelpButton
              text={
                "Es ist nicht empfohlen Preis in der Vergangenheit oder in der aktueller Vertragsperiode zu ändern. Das könnte zu unerwartete Änderungen der Zahlungsreihen führen. Preise aber der folgende Vertragsperiode können ohne Problem geändert werden."
              }
            />
          </div>
        </Modal.Header>
        <Modal.Body>
          <Table>
            <thead>
              <tr>
                <th>Ab dem</th>
                <th>Preis</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {membershipType.prices.length === 0 ? (
                <tr>
                  <td colSpan={3}>Noch kein Preis</td>
                </tr>
              ) : (
                membershipType.prices.map((price) => (
                  <tr key={price.id}>
                    <td>{formatDateNumeric(price.validFrom)}</td>
                    <td>{formatCurrency(Number.parseFloat(price.price))}</td>
                    <td>
                      <TapirButton
                        variant={"outline-danger"}
                        icon={"delete"}
                        size={"sm"}
                        onClick={() => setPriceSelectedForDeletion(price)}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
          {error !== "" && <Alert variant={"warning"}>{error}</Alert>}

          <Form>
            <div className={"d-flex gap-2 align-items-end"}>
              <div className={"d-flex gap-2"}>
                <Form.Group>
                  <Form.Label>Ab dem</Form.Label>
                  <Form.Control
                    type={"date"}
                    onChange={(event) => setAddPriceDate(event.target.value)}
                    value={addPriceDate}
                  />
                </Form.Group>
                <Form.Group>
                  <Form.Label>Preis</Form.Label>
                  <Form.Control
                    type={"number"}
                    step={0.01}
                    min={0}
                    onChange={(event) => setAddPriceAmount(event.target.value)}
                    value={addPriceAmount}
                  />
                </Form.Group>
              </div>
              <TapirButton
                variant={"primary"}
                icon={"save"}
                text={"Neuer Preis hinzufügen"}
                onClick={onAddPrice}
                disabled={error !== ""}
                loading={saving}
              />
            </div>
          </Form>
        </Modal.Body>
      </Modal>
      {priceSelectedForDeletion && (
        <ConfirmDeleteModal
          open={true}
          onConfirm={onDelete}
          loading={saving}
          onCancel={() => setPriceSelectedForDeletion(undefined)}
          message={
            'Bist du sicher das du den Preis "' +
            formatCurrency(Number.parseFloat(priceSelectedForDeletion.price)) +
            " ab dem " +
            formatDateNumeric(priceSelectedForDeletion.validFrom) +
            '" löschen willst?'
          }
        />
      )}
    </>
  );
};

export default AssociationMembershipTypePriceModal;
