import React, { useEffect, useState } from "react";
import { Product, WaitingListProductWish } from "../api-client";
import "./waiting_list_card.css";
import { ButtonGroup, Col, Form, Row, Table } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";

interface ProductWishesEditorProps {
  products: Product[];
  wishes: WaitingListProductWish[];
  setWishes: (wishes: WaitingListProductWish[]) => void;
  waitingListEntryId: string;
}

const ProductWishesEditor: React.FC<ProductWishesEditorProps> = ({
  products: products,
  wishes,
  setWishes,
  waitingListEntryId,
}) => {
  const [selectedProductTypeId, setSelectedProductTypeId] = useState<string>();
  const [selectedProductId, setSelectedProductId] = useState<string>();

  useEffect(() => {
    if (products.length === 0) return;

    setSelectedProductTypeId(products[0].type.id);
  }, [products]);

  function getProductsOfSelectedTypeNotInWishes() {
    return products
      .filter((product) => product.type.id === selectedProductTypeId)
      .filter(
        (product) =>
          !wishes.map((wish) => wish.product.id).includes(product.id),
      );
  }

  useEffect(() => {
    const productsOfType = getProductsOfSelectedTypeNotInWishes();
    if (productsOfType.length === 0) {
      setSelectedProductId(undefined);
      return;
    }

    setSelectedProductId(productsOfType[0].id);
  }, [selectedProductTypeId, wishes, products]);

  function removeWish(wishToRemove: WaitingListProductWish) {
    setWishes(
      wishes.filter((wish) => wish.product.id !== wishToRemove.product.id),
    );
  }

  function addWish() {
    const product = products.find(
      (product) => product.id === selectedProductId,
    );
    if (!product) {
      alert("Product not found. ID: " + selectedProductId);
      return;
    }
    wishes.push({
      id: undefined,
      product: product,
      quantity: 1,
      waitingListEntry: waitingListEntryId,
    });
    setWishes([...wishes]);
  }

  function updateWishQuantity(productId: string, quantity: number) {
    const wish = wishes.find((wish) => wish.product.id === productId);
    if (!wish) {
      alert("Pickup location not found. ID: " + productId);
      return;
    }

    wish.quantity = quantity;
    setWishes([...wishes]);
  }

  function getProductTypes() {
    const productTypes: { [id: string]: string } = {};
    for (const product of products) {
      productTypes[product.type.id!] = product.type.name;
    }
    return productTypes;
  }

  useEffect(() => {
    console.log(selectedProductTypeId);
  }, [selectedProductTypeId]);

  return (
    <>
      <Row>
        <h5>Produkt-Wünsche</h5>
      </Row>
      <Row>
        {wishes.length === 0 ? (
          <span className={"mb-2"}>Kein Produkt-Wunsch</span>
        ) : (
          <Table striped hover responsive>
            <thead>
              <tr>
                <th>Produkt</th>
                <th>Menge</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {wishes.map((wish) => {
                return (
                  <tr key={wish.id}>
                    <td>
                      {wish.product.type.name} {wish.product.name}
                    </td>
                    <td>
                      <Form.Control
                        size={"sm"}
                        value={wish.quantity}
                        onChange={(event) =>
                          updateWishQuantity(
                            wish.product.id!,
                            parseInt(event.target.value),
                          )
                        }
                      />
                    </td>
                    <td>
                      <ButtonGroup size={"sm"}>
                        <TapirButton
                          variant={"outline-danger"}
                          icon={"delete"}
                          onClick={() => removeWish(wish)}
                          size={"sm"}
                        />
                      </ButtonGroup>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Row>
      <Row>
        <Col>
          <Form.Select
            value={selectedProductTypeId}
            onChange={(event) => {
              setSelectedProductTypeId(event.target.value);
            }}
          >
            {Object.entries(getProductTypes()).map(
              ([productTypeId, productTypeName]) => (
                <option key={productTypeId} value={productTypeId}>
                  {productTypeName}
                </option>
              ),
            )}
          </Form.Select>
        </Col>
        <Col>
          <Form.Select
            value={selectedProductId}
            onChange={(event) => setSelectedProductId(event.target.value)}
          >
            {getProductsOfSelectedTypeNotInWishes().map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </Form.Select>
        </Col>
        <Col>
          <TapirButton
            variant={"outline-primary"}
            icon={"add_circle"}
            disabled={selectedProductId === undefined}
            onClick={() => addWish()}
          />
        </Col>
      </Row>
    </>
  );
};

export default ProductWishesEditor;
