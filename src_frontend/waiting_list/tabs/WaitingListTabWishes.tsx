import React from "react";
import { Col, Form, Row } from "react-bootstrap";
import PickupLocationWishesEditor from "../PickupLocationWishesEditor.tsx";
import ProductWishesEditor from "../ProductWishesEditor.tsx";
import {
  PickupLocation,
  Product,
  WaitingListEntryDetails,
  WaitingListPickupLocationWish,
  WaitingListProductWish
} from "../../api-client";
import formatSubscription from "../../utils/formatSubscription.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import dayjs from "dayjs";

interface WaitingListTabWishesProps {
  entryDetails: WaitingListEntryDetails;
  pickupLocations: PickupLocation[];
  pickupLocationWishes: WaitingListPickupLocationWish[];
  setPickupLocationWishes: (wishes: WaitingListPickupLocationWish[]) => void;
  products: Product[];
  productWishes: WaitingListProductWish[];
  setProductWishes: (wishes: WaitingListProductWish[]) => void;
  desiredStartDate: Date | undefined;
  setDesiredStartDate: (date: Date | undefined) => void;
  category: string;
  setCategory: (category: string) => void;
  categories: string[];
}

const WaitingListTabWishes: React.FC<WaitingListTabWishesProps> = ({
  entryDetails,
  pickupLocations,
  pickupLocationWishes,
  setPickupLocationWishes,
  products,
  productWishes,
  setProductWishes,
  category,
  setCategory,
  desiredStartDate,
  setDesiredStartDate,
  categories,
}) => {
  return (
    <>
      <Row>
        <Col>
          <Row className={"mt-2"}>
            <ProductWishesEditor
              wishes={productWishes}
              setWishes={setProductWishes}
              waitingListEntryId={entryDetails.id}
              products={products}
            />
          </Row>
          <Row className={"mt-4"}>
            <h6>Schon bestehende Verträge:</h6>
            <div>
              {(entryDetails.currentSubscriptions ?? []).length === 0 ? (
                "Keine"
              ) : (
                <ul>
                  {(entryDetails.currentSubscriptions ?? []).map(
                    (subscription) => (
                      <li key={subscription.id}>
                        {formatSubscription(subscription)} (
                        {formatDateNumeric(subscription.startDate)}
                        {" -> "}
                        {formatDateNumeric(subscription.endDate)})
                      </li>
                    ),
                  )}
                </ul>
              )}
            </div>
          </Row>
        </Col>
        <Col>
          <Row className={"mt-2"}>
            <PickupLocationWishesEditor
              pickupLocations={pickupLocations}
              setWishes={setPickupLocationWishes}
              wishes={pickupLocationWishes}
              waitingListEntryId={entryDetails.id}
            />
          </Row>
          <Row className={"mt-4"}>
            <h6>Aktuelle Abholort</h6>
            <div>
              {entryDetails.currentPickupLocation === undefined
                ? "Keine"
                : entryDetails.currentPickupLocation.name}
            </div>
          </Row>
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
            <Form.Label>Kategorie</Form.Label>
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
    </>
  );
};

export default WaitingListTabWishes;
