import React, { useEffect, useState } from "react";
import { Card, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import { PublicProductType, PublicSubscription } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import ProductForm from "../../bestell_wizard/components/ProductForm.tsx";
import { ShoppingCart } from "../../bestell_wizard/types/ShoppingCart.ts";

interface SubscriptionEditModalProps {
  show: boolean;
  onHide: () => void;
  subscriptions: PublicSubscription[];
  productType: PublicProductType;
}

const SubscriptionEditModal: React.FC<SubscriptionEditModalProps> = ({
  show,
  onHide,
  subscriptions,
  productType,
}) => {
  const [shoppingCart, setShoppingCart] = useState<ShoppingCart>({});

  useEffect(() => {
    const shoppingCart: ShoppingCart = Object.fromEntries(
      productType.products.map((product) => [product.id, 0]),
    );
    for (const subscription of subscriptions) {
      shoppingCart[subscription.productId] = subscription.quantity;
    }
    setShoppingCart(shoppingCart);
  }, [subscriptions]);

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>{productType.name} bearbeiten</h5>
      </Modal.Header>
      <Modal.Body style={{ maxHeight: "65vh", overflowY: "scroll" }}>
        <ProductForm
          productType={productType}
          shoppingCart={shoppingCart}
          setShoppingCart={setShoppingCart}
        />
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
          />
          <TapirButton
            variant={"primary"}
            icon={"contract_edit"}
            text={"Vertrag anpassen"}
          />
        </div>
      </Card.Footer>
    </Modal>
  );
};

export default SubscriptionEditModal;
