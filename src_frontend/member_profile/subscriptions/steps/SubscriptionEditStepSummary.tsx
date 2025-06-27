import React from "react";
import SummaryProductTypeTable from "../../../bestell_wizard/components/SummaryProductTypeTable.tsx";
import SummaryPickupLocations from "../../../bestell_wizard/components/SummaryPickupLocations.tsx";
import { PublicPickupLocation, PublicProductType } from "../../../api-client";
import { ShoppingCart } from "../../../bestell_wizard/types/ShoppingCart.ts";
import { Modal } from "react-bootstrap";
import TapirButton from "../../../components/TapirButton.tsx";

interface SubscriptionEditStepSummaryProps {
  waitingListModeEnabled: boolean;
  firstDeliveryDatesByProductType: { [key: string]: Date };
  productType: PublicProductType;
  shoppingCart: ShoppingCart;
  selectedPickupLocations: PublicPickupLocation[];
  onBackClicked: () => void;
  onConfirmClicked: () => void;
  loading: boolean;
}

const SubscriptionEditStepSummary: React.FC<
  SubscriptionEditStepSummaryProps
> = ({
  waitingListModeEnabled,
  firstDeliveryDatesByProductType,
  productType,
  shoppingCart,
  selectedPickupLocations,
  onBackClicked,
  onConfirmClicked,
  loading,
}) => {
  return (
    <>
      <Modal.Body>
        <SummaryProductTypeTable
          waitingListModeEnabled={waitingListModeEnabled}
          firstDeliveryDatesByProductType={firstDeliveryDatesByProductType}
          productType={productType}
          shoppingCart={shoppingCart}
        />
        <SummaryPickupLocations
          selectedPickupLocations={selectedPickupLocations}
          waitingListModeEnabled={waitingListModeEnabled}
        />
      </Modal.Body>
      <Modal.Footer>
        <div
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <TapirButton
            variant={"outline-secondary"}
            icon={"chevron_left"}
            iconPosition={"left"}
            text={"Zurück"}
            onClick={onBackClicked}
          />
          <TapirButton
            variant={"primary"}
            icon={"contract_edit"}
            text={
              waitingListModeEnabled
                ? "Warteliste-Eintrag bestätigen"
                : "Vertrag bestätigen"
            }
            iconPosition={"right"}
            onClick={onConfirmClicked}
            loading={loading}
          />
        </div>
      </Modal.Footer>
    </>
  );
};

export default SubscriptionEditStepSummary;
