import React, { useEffect, useRef, useState } from "react";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProduct, PublicProductType } from "../../api-client";
import { Carousel, Form, Modal } from "react-bootstrap";
import { BestellWizardSettings } from "../../bestell_wizard/types/BestellWizardSettings.ts";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { isProductTypeOrdered } from "../../bestell_wizard/utils/isProductTypeOrdered.ts";
import { formatShoppingCart } from "../../bestell_wizard/utils/formatShoppingCart.ts";
import { doesProductBelongsToProductType } from "../../bestell_wizard/utils/doesProductBelongToProductType.ts";
import NextStepButton from "../components/NextStepButton.tsx";
import { BUTTON_VARIANT } from "../utils/BUTTON_VARIANT.ts";
import { CarouselRef } from "react-bootstrap/Carousel";
import Step4BProductOrder from "../components/Step4BProductOrder.tsx";

interface Step4BProductTypeOrderProps {
  settings: BestellWizardSettings;
  productType: PublicProductType;
  goToNextStep: () => void;
  shoppingCart: ShoppingCart;
  setShoppingCart: (cart: ShoppingCart) => void;
  active: boolean;
  checkingCapacities: boolean;
  waitingListLinkConfirmationModeEnabled: boolean;
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
  active,
  checkingCapacities,
  waitingListLinkConfirmationModeEnabled,
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
    if (!active) {
      setTimeout(() => setShowValidation(false), 200);
    }
  }, [active]);

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

  return (
    <>
      {productType.products.length <= 2 ? (
        <div className={"d-flex flex-row"}>
          {productType.products
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
          defaultActiveIndex={productType.products.length > 1 ? 1 : 0}
        >
          {productType.products
            .toSorted((a, b) => a.price - b.price)
            .map((product, index) => (
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
