import React, { useEffect, useRef, useState } from "react";
import { Carousel, Form, Modal } from "react-bootstrap";
import { CarouselRef } from "react-bootstrap/Carousel";
import {
  PublicProduct,
  PublicProductType,
  PublicWaitingListEntryDetails,
} from "../../api-client";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import TapirButton from "../../components/TapirButton.tsx";
import NextStepButton from "../components/NextStepButton.tsx";
import Step4BProductOrder from "../components/Step4BProductOrder.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";

interface Step4BProductTypeOrderProps {
  settings: BestellWizardSettings;
  productType: PublicProductType;
  goToNextStep: () => void;
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
  stepActive: boolean;
  checkingCapacities: boolean;
  waitingListLinkConfirmationModeEnabled: boolean;
  waitingListEntryDetails: PublicWaitingListEntryDetails | undefined;
  productIdsOverCapacity: string[];
  productTypeIdsOverCapacity: string[];
  productTypesInWaitingList: Set<PublicProductType>;
  isOrderStep: boolean;
  nextButtonTextOverride?: string;
  orderLoading: boolean;
}

const Step4BProductTypeOrder: React.FC<Step4BProductTypeOrderProps> = ({
  settings,
  productType,
  goToNextStep,
  shoppingCart,
  setShoppingCart,
  stepActive,
  checkingCapacities,
  waitingListLinkConfirmationModeEnabled,
  waitingListEntryDetails,
  productIdsOverCapacity,
  productTypeIdsOverCapacity,
  productTypesInWaitingList,
  isOrderStep,
  nextButtonTextOverride,
  orderLoading,
}) => {
  const carouselRef = useRef<CarouselRef>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [waitingListInfoModalOpen, setWaitingListInfoModalOpen] =
    useState(false);

  useEffect(() => {
    if (!stepActive) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [stepActive]);

  function validate() {
    setShowValidation(true);
    if (
      productType.mustBeSubscribedTo &&
      !isProductTypeOrdered(productType, shoppingCart)
    ) {
      return;
    }

    goToNextStep();
  }

  function getNextButtonText() {
    if (nextButtonTextOverride) {
      return nextButtonTextOverride;
    }

    if (!isProductTypeOrdered(productType, shoppingCart)) {
      return "Weiter ohne " + productType.name;
    }

    const filteredShoppingCart = Object.fromEntries(
      Object.entries(shoppingCart).filter(([productId, _]) =>
        doesProductBelongsToProductType(productId, productType),
      ),
    );

    if (productTypesInWaitingList.has(productType)) {
      return (
        "Weiter mit Warteliste: " +
        formatShoppingCart(filteredShoppingCart, settings)
      );
    }

    return "Weiter mit " + formatShoppingCart(filteredShoppingCart, settings);
  }

  function buildProduct(
    product: PublicProduct,
    index: number,
    showCarouselArrows: boolean,
  ) {
    return (
      <Step4BProductOrder
        product={product}
        productType={productType}
        settings={settings}
        productTypeIdsOverCapacity={productTypeIdsOverCapacity}
        productIdsOverCapacity={productIdsOverCapacity}
        shoppingCart={shoppingCart}
        setShoppingCart={setShoppingCart}
        waitingListLinkConfirmationModeEnabled={
          waitingListLinkConfirmationModeEnabled
        }
        showValidation={showValidation}
        setWaitingListInfoModalOpen={setWaitingListInfoModalOpen}
        showCarouselArrows={showCarouselArrows}
        index={index}
        carouselRef={carouselRef}
      />
    );
  }

  function getRelevantProducts() {
    if (!waitingListEntryDetails) {
      return productType.products.filter(
        (product) => !product.hiddenInBestellWizard,
      );
    }

    const allProducts = [...productType.products];
    const wishedProductIds = (waitingListEntryDetails.productWishes ?? []).map(
      (productWish) => productWish.product.id,
    );
    const mustInclude = productType.products.filter(
      (product) =>
        !product.hiddenInBestellWizard ||
        (waitingListEntryDetails.productWishes ?? [])
          .map((productWish) => productWish.product.id)
          .includes(product.id),
    );
    const mustInclude2 = productType.products.filter((product) =>
      (waitingListEntryDetails.productWishes ?? [])
        .map((productWish) => productWish.product.id)
        .includes(product.id),
    );
    return mustInclude;
  }

  return (
    <>
      {getRelevantProducts().length <= 2 ? (
        <div className={"d-flex flex-row gap-2"}>
          {getRelevantProducts()
            .toSorted((a, b) => a.price - b.price)
            .map((product, index) => (
              <div key={product.id}>{buildProduct(product, index, false)}</div>
            ))}
        </div>
      ) : (
        <Carousel
          indicators={false}
          controls={false}
          interval={null}
          touch={true}
          style={{ width: "100%" }}
          variant={"dark"}
          ref={carouselRef}
          wrap={false}
          defaultActiveIndex={getRelevantProducts().length > 1 ? 1 : 0}
        >
          {getRelevantProducts().map((product, index) => (
            <Carousel.Item key={product.id}>
              {buildProduct(product, index, true)}
            </Carousel.Item>
          ))}
        </Carousel>
      )}

      {showValidation &&
        !isProductTypeOrdered(productType, shoppingCart) &&
        productType.mustBeSubscribedTo && (
          <Form.Control.Feedback
            type="invalid"
            style={{ display: "block" }}
            className={"text-center"}
          >
            Dieses Produkt muss bestellt werden.
          </Form.Control.Feedback>
        )}
      <NextStepButton
        onClick={validate}
        text={getNextButtonText()}
        loading={checkingCapacities || orderLoading}
        isOrderStep={isOrderStep}
        stepActive={stepActive}
      />
      <Modal
        show={waitingListInfoModalOpen}
        onHide={() => setWaitingListInfoModalOpen(false)}
        centered={true}
      >
        <Modal.Header>
          {settings.strings.step4bWaitingListModalTitle}
        </Modal.Header>
        <Modal.Body>
          <p
            dangerouslySetInnerHTML={{
              __html: settings.strings.step4bWaitingListModalText,
            }}
          ></p>
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            text={"Schließen"}
            variant={BUTTON_VARIANT}
            onClick={() => setWaitingListInfoModalOpen(false)}
            icon={"close"}
          />
        </Modal.Footer>
      </Modal>
    </>
  );
};

export default Step4BProductTypeOrder;
