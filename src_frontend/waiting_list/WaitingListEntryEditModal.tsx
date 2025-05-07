import React, { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi.ts";
import { WaitingListApi, WaitingListEntryDetails } from "../api-client";
import "./waiting_list_card.css";
import { Col, Form, Modal, Row } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface WaitingListEntryEditModalProps {
  csrfToken: string;
  entryDetails: WaitingListEntryDetails;
  show: boolean;
  onClose: () => void;
  reloadEntries: () => void;
}

const WaitingListEntryEditModal: React.FC<WaitingListEntryEditModalProps> = ({
  csrfToken,
  entryDetails,
  show,
  onClose,
  reloadEntries,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [showConfirmDeleteModal, setShowConfirmDeleteModal] = useState(false);
  const [deletionLoading, setDeletionLoading] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [street, setStreet] = useState("");
  const [street2, setStreet2] = useState("");
  const [postcode, setPostcode] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");

  useEffect(() => {
    setFirstName(entryDetails.firstName);
    setLastName(entryDetails.lastName);
    setEmail(entryDetails.email);
    setPhoneNumber(entryDetails.phoneNumber);
    setStreet(entryDetails.street);
    setStreet2(entryDetails.street2);
    setPostcode(entryDetails.postcode);
    setCity(entryDetails.city);
    setCountry(entryDetails.country);
  }, [entryDetails]);

  function onConfirmDelete() {
    setDeletionLoading(true);
    api
      .waitingListWaitingListEntriesDestroy({ id: entryDetails.id })
      .then(() => reloadEntries())
      .catch(handleRequestError)
      .finally(() => setDeletionLoading(false));
  }

  return (
    <>
      <Modal
        show={show && !showConfirmDeleteModal}
        onHide={onClose}
        centered={true}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>
            Warteliste-Eintrag bearbeiten: {entryDetails.firstName}{" "}
            {entryDetails.lastName}
          </h5>
        </Modal.Header>
        <Modal.Body>
          <Form>
            {entryDetails.memberAlreadyExists && (
              <Row>
                <Form.Text>
                  Dieses Eintrag bezieht sich auf ein bestehendes Mitglied,
                  deswegen können die Stammdaten hier nicht geändert werden.
                </Form.Text>
              </Row>
            )}
            <Row className={"mt-2"}>
              <Col>
                <Form.Group controlId={"form.first_name"}>
                  <Form.Label>First Name</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Vorname"}
                    onChange={(event) => setFirstName(event.target.value)}
                    required={true}
                    value={firstName}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group controlId={"form.last_name"}>
                  <Form.Label>Last Name</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Nachname"}
                    onChange={(event) => setLastName(event.target.value)}
                    required={true}
                    value={lastName}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
            </Row>
            <Row className={"mt-2"}>
              <Col>
                <Form.Group controlId={"form.email"}>
                  <Form.Label>Email</Form.Label>
                  <Form.Control
                    type={"email"}
                    placeholder={"E-Mail"}
                    onChange={(event) => setEmail(event.target.value)}
                    required={true}
                    value={email}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group controlId={"form.phone_number"}>
                  <Form.Label>Telefonnummer</Form.Label>
                  <Form.Control
                    type={"tel"}
                    placeholder={"Telefonnummer"}
                    onChange={(event) => setPhoneNumber(event.target.value)}
                    required={true}
                    value={phoneNumber}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
            </Row>
            <Row>
              <Col>
                <Form.Group controlId={"form.street"}>
                  <Form.Label>Adresse</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Adresse"}
                    onChange={(event) => setStreet(event.target.value)}
                    required={true}
                    value={street}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group controlId={"form.street2"}>
                  <Form.Label>Adresse (Ergänzung)</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Adresse (Ergänzung)"}
                    onChange={(event) => setStreet2(event.target.value)}
                    required={true}
                    value={street2}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
            </Row>
            <Row className={"mt-2"}>
              <Col>
                <Form.Group controlId={"form.postcode"}>
                  <Form.Label>Postleitzahl</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Postleitzahl"}
                    onChange={(event) => setPostcode(event.target.value)}
                    required={true}
                    value={postcode}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group controlId={"form.city"}>
                  <Form.Label>Stadt</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Stadt"}
                    onChange={(event) => setCity(event.target.value)}
                    required={true}
                    value={city}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group controlId={"form.country"}>
                  <Form.Label>Land</Form.Label>
                  <Form.Control
                    type={"text"}
                    placeholder={"Land"}
                    onChange={(event) => setCountry(event.target.value)}
                    required={true}
                    value={country}
                    disabled={entryDetails.memberAlreadyExists}
                  />
                </Form.Group>
              </Col>
            </Row>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"danger"}
            icon={"delete"}
            text={"Löschen"}
            onClick={() => setShowConfirmDeleteModal(true)}
          />
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Speichern"}
            onClick={() => alert("TODO")}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmDeleteModal
        onConfirm={onConfirmDelete}
        message={
          "Möchtest du wirklich der Eintrag von " +
          entryDetails.firstName +
          " " +
          entryDetails.lastName +
          " aus der Warteliste löschen?"
        }
        open={showConfirmDeleteModal}
        onCancel={() => setShowConfirmDeleteModal(false)}
        loading={deletionLoading}
      />
    </>
  );
};

export default WaitingListEntryEditModal;
