import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { StaticSegment, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import TapirButton from "../TapirButton";

interface CreateRecipientModalProps {
  open: boolean;
  onClose: () => void;
  segment: StaticSegment;
}

const CreateRecipientModal: React.FC<CreateRecipientModalProps> = ({
  open,
  onClose,
  segment,
}) => {
  const [loading, setLoading] = useState(false);
  const recipientApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [firstNameError, setFirstNameError] = useState<string | undefined>();
  const [lastNameError, setLastNameError] = useState<string | undefined>();
  const [emailError, setEmailError] = useState<string | undefined>();

  function onCreateClicked() {
    setLoading(true);

    recipientApi
      .tapirmailApiStaticSegmentRecipientCreate({
        staticSegmentRecipientRequest: {
          firstName: firstName,
          lastName: lastName,
          email: email,
          segment: segment.id!,
        },
      })
      .then(() => {
        onClose();
        setFirstName("");
        setLastName("");
        setEmail("");
      })
      .catch((error) => {
        setFirstNameError(undefined);
        setLastNameError(undefined);
        setEmailError(undefined);

        error.response
          .json()
          .then((fieldErrors: Record<string, string[]>) => {
            if ("first_name" in fieldErrors) {
              setFirstNameError(fieldErrors["first_name"][0]);
            }
            if ("last_name" in fieldErrors) {
              setLastNameError(fieldErrors["last_name"][0]);
            }
            if ("email" in fieldErrors) {
              setEmailError(fieldErrors["email"][0]);
            }
          })
          .catch(() => {
            console.error(error);
            showAlert("Fehler beim erzeugen der Segment", "danger");
          });
      })
      .finally(() => {
        setLoading(false);
      });
  }

  return (
    <Modal show={open} onHide={onClose} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>Empfänger zu {segment.name} hinzufügen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group>
            <Form.Label column={"lg"}>Vorname</Form.Label>
            <Form.Control
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              isInvalid={!!firstNameError}
            />
            {firstNameError && (
              <div className={"invalid-feedback"}>{firstNameError}</div>
            )}
          </Form.Group>
          <Form.Group>
            <Form.Label column={"lg"}>Nachname</Form.Label>
            <Form.Control
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              isInvalid={!!lastNameError}
            />
            {lastNameError && (
              <div className={"invalid-feedback"}>{lastNameError}</div>
            )}
          </Form.Group>
          <Form.Group>
            <Form.Label column={"lg"}>Email-Adresse</Form.Label>
            <Form.Control
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              isInvalid={!!emailError}
            />
            {emailError && (
              <div className={"invalid-feedback"}>{emailError}</div>
            )}
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer className="d-flex justify-content-end align-items-center">
        <TapirButton
          variant={"primary"}
          text={loading ? "Loading..." : "Hinzufügen"}
          icon={PlusCircleIcon}
          disabled={loading}
          onClick={() => onCreateClicked()}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default CreateRecipientModal;
