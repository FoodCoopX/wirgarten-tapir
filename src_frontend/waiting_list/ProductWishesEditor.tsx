import React from "react";
import { Product, WaitingListProductWish } from "../api-client";
import "./waiting_list_card.css";
import { ButtonGroup, Form, Row, Table } from "react-bootstrap";
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
  function removeWish(wishToRemove: WaitingListProductWish) {
    setWishes(
      wishes.filter((wish) => wish.product.id !== wishToRemove.product.id),
    );
  }

  function addWish(productId: string) {
    const product = products.find((product) => product.id === productId);
    if (!product) {
      alert("Pickup location not found. ID: " + productId);
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
        <Form.Select onChange={(event) => addWish(event.target.value)}>
          <option value={-1}>Produkt-Wunsch hinzufügen</option>
          {products
            .filter(
              (product) =>
                !wishes.map((wish) => wish.product.id).includes(product.id),
            )
            .map((product) => (
              <option key={product.id} value={product.id}>
                {product.type.name} {product.name}
              </option>
            ))}
        </Form.Select>
      </Row>
    </>
  );
};

export default ProductWishesEditor;
