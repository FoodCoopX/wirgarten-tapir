import React from "react";
import { Col, Row } from "react-bootstrap";
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

interface WaitingListTabWishesProps {
  entryDetails: WaitingListEntryDetails;
  pickupLocations: PickupLocation[];
  pickupLocationWishes: WaitingListPickupLocationWish[];
  setPickupLocationWishes: (wishes: WaitingListPickupLocationWish[]) => void;
  products: Product[];
  productWishes: WaitingListProductWish[];
  setProductWishes: (wishes: WaitingListProductWish[]) => void;
}

const WaitingListTabWishes: React.FC<WaitingListTabWishesProps> = ({
  entryDetails,
  pickupLocations,
  pickupLocationWishes,
  setPickupLocationWishes,
  products,
  productWishes,
  setProductWishes,
}) => {
  return (
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
  );
};

export default WaitingListTabWishes;
