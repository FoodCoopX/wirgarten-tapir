import React, { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi.ts";
import {
  PickupLocation,
  Product,
  WaitingListApi,
  WaitingListEntryDetails,
  WaitingListPickupLocationWish,
  WaitingListProductWish,
} from "../api-client";
import "./waiting_list_card.css";
import { Col, Form, Modal, Row } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";
import dayjs from "dayjs";
import PickupLocationWishesEditor from "./PickupLocationWishesEditor.tsx";
import ProductWishesEditor from "./ProductWishesEditor.tsx";

interface WaitingListEntryEditModalProps {
  csrfToken: string;
  entryDetails: WaitingListEntryDetails;
  show: boolean;
  onClose: () => void;
  reloadEntries: () => void;
  pickupLocations: PickupLocation[];
  products: Product[];
  categories: string[];
}

const WaitingListEntryEditModal: React.FC<WaitingListEntryEditModalProps> = ({
  csrfToken,
  entryDetails,
  show,
  onClose,
  reloadEntries,
  pickupLocations,
  products,
  categories,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [showConfirmDeleteModal, setShowConfirmDeleteModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [street, setStreet] = useState("");
  const [street2, setStreet2] = useState("");
  const [postcode, setPostcode] = useState("");
  const [city, setCity] = useState("");
  const [desiredStartDate, setDesiredStartDate] = useState<Date>();
  const [pickupLocationWishes, setPickupLocationWishes] = useState<
    WaitingListPickupLocationWish[]
  >([]);
  const [productWishes, setProductWishes] = useState<WaitingListProductWish[]>(
    [],
  );
  const [comment, setComment] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    setFirstName(entryDetails.firstName);
    setLastName(entryDetails.lastName);
    setEmail(entryDetails.email);
    setPhoneNumber(entryDetails.phoneNumber);
    setStreet(entryDetails.street);
    setStreet2(entryDetails.street2);
    setPostcode(entryDetails.postcode);
    setCity(entryDetails.city);
    setDesiredStartDate(entryDetails.desiredStartDate);
    setPickupLocationWishes(entryDetails.pickupLocationWishes ?? []);
    setProductWishes(entryDetails.productWishes ?? []);
    setComment(entryDetails.comment);
    setCategory(entryDetails.category ?? "");
  }, [entryDetails]);

  function onConfirmDelete() {
    setLoading(true);
    api
      .waitingListWaitingListEntriesDestroy({ id: entryDetails.id })
      .then(() => reloadEntries())
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }

  function onSave() {
    setLoading(true);

    pickupLocationWishes.sort((a, b) => a.priority - b.priority);
    api
      .waitingListApiUpdateEntryCreate({
        waitingListEntryUpdateRequest: {
          firstName: firstName,
          lastName: lastName,
          email: email,
          phoneNumber: phoneNumber,
          street: street,
          street2: street2,
          postcode: postcode,
          city: city,
          desiredStartDate: desiredStartDate,
          category: category,
          comment: comment,
          id: entryDetails.id,
          pickupLocationIds: pickupLocationWishes.map(
            (wish) => wish.pickupLocation.id!,
          ),
          productIds: productWishes.map((wish) => wish.product.id!),
          productQuantities: productWishes.map((wish) => wish.quantity),
        },
      })
      .then(() => {
        reloadEntries();
        onClose();
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Modal
        show={show && !showConfirmDeleteModal}
        onHide={onClose}
        centered={true}
        size={"xl"}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>
            Warteliste-Eintrag bearbeiten: {entryDetails.firstName}{" "}
            {entryDetails.lastName}
          </h5>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Row>
              <Col>
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
                    <Form.Group controlId={"form.desiredStartDate"}>
                      <Form.Label>Gewünschtes Anfangsdatum</Form.Label>
                      <Form.Control
                        type={"date"}
                        onChange={(event) => {
                          setDesiredStartDate(
                            !event.target.value
                              ? undefined
                              : new Date(event.target.value),
                          );
                        }}
                        value={
                          desiredStartDate === undefined
                            ? undefined
                            : dayjs(desiredStartDate).format("YYYY-MM-DD")
                        }
                        required={false}
                      />
                    </Form.Group>
                  </Col>
                  <Col>
                    <Form.Group controlId={"form.category"}>
                      <Form.Label>Category</Form.Label>
                      <Form.Select
                        onChange={(event) => setCategory(event.target.value)}
                        value={category}
                      >
                        <option value={""}>Keine Kategorie</option>
                        {categories.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </Form.Select>
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
              </Col>
              <Col>
                <Row>
                  <PickupLocationWishesEditor
                    pickupLocations={pickupLocations}
                    setWishes={setPickupLocationWishes}
                    wishes={pickupLocationWishes}
                    waitingListEntryId={entryDetails.id}
                  />
                </Row>
                <Row className={"mt-2"}>
                  <ProductWishesEditor
                    wishes={productWishes}
                    setWishes={setProductWishes}
                    waitingListEntryId={entryDetails.id}
                    products={products}
                  />
                </Row>
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
            loading={loading}
          />
          <TapirButton
            variant={"primary"}
            icon={"save"}
            text={"Speichern"}
            onClick={onSave}
            loading={loading}
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
        loading={loading}
      />
    </>
  );
};

export default WaitingListEntryEditModal;
