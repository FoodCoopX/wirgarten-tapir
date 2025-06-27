import React, { useEffect, useState } from "react";
import { Card, Col, Form, Modal, Row } from "react-bootstrap";
import "dayjs/locale/de";
import {
  PublicProductType,
  PublicSubscription,
  SubscriptionsApi,
} from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import ProductForm from "../../bestell_wizard/components/ProductForm.tsx";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";
import { getTextSepaCheckbox } from "../../bestell_wizard/utils/getTextSepaCheckbox.ts";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface SubscriptionEditModalProps {
  show: boolean;
  onHide: () => void;
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
  memberId: string;
  reloadSubscriptions: () => void;
}

const SubscriptionEditModal: React.FC<SubscriptionEditModalProps> = ({
  show,
  onHide,
  subscriptions,
  productType,
  memberId,
  reloadSubscriptions,
}) => {
  const api = useApi(SubscriptionsApi, getCsrfToken());

  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});
  const [sepaAllowed, setSepaAllowed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [orderConfirmed, setOrderConfirmed] = useState(false);
  const [orderError, setOrderError] = useState("");

  useEffect(() => {
    const shoppingCart: ShoppingCart = Object.fromEntries(
      productType.products.map((product) => [product.id, 0]),
    );
    for (const subscription of subscriptions) {
      shoppingCart[subscription.productId] = subscription.quantity;
    }
    setShoppingCart(shoppingCart);
  }, [subscriptions]);

  function onConfirm() {
    setLoading(true);

    api
      .subscriptionsApiUpdateSubscriptionCreate({
        updateSubscriptionsRequestRequest: {
          memberId: memberId,
          shoppingCart: shoppingCart,
          sepaAllowed: sepaAllowed,
          productTypeId: productType.id!,
        },
      })
      .then((response) => {
        setShowConfirmationModal(true);
        setOrderConfirmed(response.orderConfirmed);
        if (response.orderConfirmed) {
          reloadSubscriptions();
          onHide();
        } else {
          setOrderError(response.error!);
        }
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Modal
        show={show && !showConfirmationModal}
        onHide={onHide}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>{productType.name} bearbeiten</h5>
        </Modal.Header>
        <Modal.Body style={{ maxHeight: "65vh", overflowY: "scroll" }}>
          <Row>
            <Col>
              <ProductForm
                productType={productType}
                shoppingCart={shoppingCart}
                setShoppingCart={setShoppingCart}
              />
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Check
                id={"sepa-mandat"}
                label={getTextSepaCheckbox()}
                checked={sepaAllowed}
                onChange={(event) => setSepaAllowed(event.target.checked)}
              />
            </Col>
          </Row>
        </Modal.Body>
        <Card.Footer>
          <div
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <TapirButton
              variant={"outline-secondary"}
              icon={"cancel"}
              iconPosition={"left"}
              text={"Abbrechen"}
              onClick={onHide}
            />
            <TapirButton
              variant={"primary"}
              icon={"contract_edit"}
              text={
                sepaAllowed
                  ? "Vertrag anpassen"
                  : "Ermächtige das SEPA-Mandat um weiter zu gehen"
              }
              iconPosition={"right"}
              disabled={!sepaAllowed}
              loading={loading}
              onClick={onConfirm}
            />
          </div>
        </Card.Footer>
      </Modal>
      <Modal
        show={showConfirmationModal && orderConfirmed}
        onHide={() => setShowConfirmationModal(false)}
        centered={true}
        className={"bg-success"}
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Bestellung bestätigt</h5>
        </Modal.Header>
        <Modal.Footer>
          <TapirButton
            variant={"outline-secondary"}
            icon={"check"}
            onClick={() => setShowConfirmationModal(false)}
            text={"Weiter"}
          />
        </Modal.Footer>
      </Modal>
      <Modal
        show={showConfirmationModal && !orderConfirmed}
        onHide={() => setShowConfirmationModal(false)}
        centered={true}
      >
        <Modal.Header closeButton className={"bg-warning"}>
          <h5 className={"mb-0"}>
            Deine Bestellung könnte nicht bestätigt werden
          </h5>
        </Modal.Header>
        <Modal.Body>{orderError}</Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"outline-secondary"}
            icon={"edit"}
            onClick={() => setShowConfirmationModal(false)}
            text={"Bestellung anpassen"}
          />
        </Modal.Footer>
      </Modal>
    </>
  );
};

export default SubscriptionEditModal;
