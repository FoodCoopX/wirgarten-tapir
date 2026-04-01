import React from "react";
import { Col, Form, Row } from "react-bootstrap";
import { WaitingListEntryDetails } from "../../api-client";

interface WaitingListTabPersonalDataProps {
  entryDetails: WaitingListEntryDetails;
  firstName: string;
  setFirstName: (name: string) => void;
  lastName: string;
  setLastName: (name: string) => void;
  email: string;
  setEmail: (name: string) => void;
  phoneNumber: string;
  setPhoneNumber: (name: string) => void;
  street: string;
  setStreet: (street: string) => void;
  street2: string;
  setStreet2: (street2: string) => void;
  postcode: string;
  setPostcode: (postcode: string) => void;
  city: string;
  setCity: (city: string) => void;
  comment: string;
  setComment: (comment: string) => void;
}

const WaitingListTabPersonalData: React.FC<WaitingListTabPersonalDataProps> = ({
  entryDetails,
  firstName,
  setFirstName,
  lastName,
  setLastName,
  email,
  setEmail,
  phoneNumber,
  setPhoneNumber,
  street,
  setStreet,
  street2,
  setStreet2,
  postcode,
  setPostcode,
  city,
  setCity,
  comment,
  setComment,
}) => {
  return (
    <>
      {entryDetails.memberAlreadyExists && (
        <Row className={"mt-2"}>
          <Form.Text>
            Dieses Eintrag bezieht sich auf ein bestehendes Mitglied, deswegen
            können die Stammdaten hier nicht geändert werden.
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
      <Row className={"mt-2"}>
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
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <Form.Label>Kommentar</Form.Label>
          <Form.Control
            as={"textarea"}
            type={"text"}
            placeholder={"Kommentar"}
            onChange={(event) => setComment(event.target.value)}
            value={comment}
          />
        </Col>
      </Row>
    </>
  );
};

export default WaitingListTabPersonalData;
