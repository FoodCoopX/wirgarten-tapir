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
import { Modal, Tab, Tabs } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";
import WaitingListTabPersonalData from "./tabs/WaitingListTabPersonalData.tsx";
import WaitingListTabWishes from "./tabs/WaitingListTabWishes.tsx";
import WaitingListTabLink from "./tabs/WaitingListTabLink.tsx";

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

  function buildTitle() {
    const content = entryDetails.firstName + " " + entryDetails.lastName;
    if (entryDetails.urlToMemberProfile) {
      return <a href={entryDetails.urlToMemberProfile}>{content}</a>;
    } else {
      return content;
    }
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
            Warteliste-Eintrag bearbeiten: {buildTitle()}
          </h5>
        </Modal.Header>
        <Modal.Body>
          <Tabs defaultActiveKey={"personal_data"}>
            <Tab eventKey="personal_data" title="Persönliche Daten">
              <WaitingListTabPersonalData
                categories={categories}
                entryDetails={entryDetails}
                firstName={firstName}
                setFirstName={setFirstName}
                lastName={lastName}
                setLastName={setLastName}
                email={email}
                setEmail={setEmail}
                phoneNumber={phoneNumber}
                setPhoneNumber={setPhoneNumber}
                street={street}
                setStreet={setStreet}
                street2={street2}
                setStreet2={setStreet2}
                postcode={postcode}
                setPostcode={setPostcode}
                city={city}
                setCity={setCity}
                desiredStartDate={desiredStartDate}
                setDesiredStartDate={setDesiredStartDate}
                category={category}
                setCategory={setCategory}
                comment={comment}
                setComment={setComment}
              />
            </Tab>
            <Tab eventKey="wishes" title="Wünsche">
              <WaitingListTabWishes
                entryDetails={entryDetails}
                pickupLocations={pickupLocations}
                pickupLocationWishes={pickupLocationWishes}
                setPickupLocationWishes={setPickupLocationWishes}
                products={products}
                productWishes={productWishes}
                setProductWishes={setProductWishes}
              />
            </Tab>
            <Tab eventKey="link" title="Link">
              <WaitingListTabLink entryDetails={entryDetails} />
            </Tab>
          </Tabs>
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"outline-danger"}
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
