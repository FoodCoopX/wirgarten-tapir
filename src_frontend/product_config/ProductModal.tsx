import React, { useEffect, useState } from "react";
import {
  Col,
  Form,
  ListGroup,
  Modal,
  Row,
  Spinner,
  Table,
} from "react-bootstrap";
import {
  PickingModeEnum,
  ProductBasketSizeEquivalence,
  SubscriptionsApi,
} from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import TapirButton from "../components/TapirButton.tsx";
import {
  getPeriodIdFromUrl,
  getProductIdFromUrl,
} from "./get_parameter_from_url.ts";

interface ProductModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
}

const ProductModal: React.FC<ProductModalProps> = ({
  show,
  onHide,
  csrfToken,
}) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [productName, setProductName] = useState<string>("");
  const [isBaseProduct, setIsBaseProduct] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [price, setPrice] = useState(0);
  const [size, setSize] = useState(0);
  const [equivalences, setEquivalences] = useState<
    ProductBasketSizeEquivalence[]
  >([]);
  const [pickingMode, setPickingMode] = useState<PickingModeEnum>(
    PickingModeEnum.Share,
  );
  const [dataLoading, setDataLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!show) return;

    setDataLoading(true);

    if (!getProductIdFromUrl()) return;

    api
      .subscriptionsApiExtendedProductRetrieve({
        productId: getProductIdFromUrl(),
      })
      .then((extendedProduct) => {
        setProductName(extendedProduct.name);
        setIsBaseProduct(extendedProduct.base);
        setDeleted(extendedProduct.deleted);
        setPrice(extendedProduct.price);
        setSize(extendedProduct.size);
        setEquivalences(extendedProduct.basketSizeEquivalences);
        setPickingMode(extendedProduct.pickingMode);
      })
      .catch(alert)
      .finally(() => setDataLoading(false));
  }, [show]);

  function onSave() {
    const form = document.getElementById("productForm") as HTMLFormElement;
    if (!form.reportValidity()) return;

    setSaving(true);

    api
      .subscriptionsApiExtendedProductPartialUpdate({
        patchedExtendedProductRequest: {
          id: getProductIdFromUrl(),
          name: productName,
          base: isBaseProduct,
          size: size,
          price: price,
          basketSizeEquivalences: equivalences,
          deleted: deleted,
          growingPeriodId: getPeriodIdFromUrl(),
        },
      })
      .then(() => location.reload())
      .catch(alert)
      .finally(() => setSaving(false));
    return;
  }

  function onEquivalenceChanged(index: number, value: number) {
    const newEquivalences = [...equivalences];
    newEquivalences[index].quantity = value;
    setEquivalences(newEquivalences);
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <ListGroup variant={"flush"}>
        <Form id={"productForm"}>
          <ListGroup.Item>
            <Row>
              <Col>
                <Form.Group>
                  <Form.Label>Produkt Name</Form.Label>
                  <Form.Control
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    placeholder={"Produkt Name"}
                  />
                </Form.Group>
              </Col>
              <Col>
                <Form.Group>
                  <Form.Label>Ist Basisprodukt</Form.Label>
                  <Form.Check
                    checked={isBaseProduct}
                    onChange={(e) => setIsBaseProduct(e.target.checked)}
                  />
                </Form.Group>
              </Col>
            </Row>
          </ListGroup.Item>
          <ListGroup.Item>
            <Row>
              <Col>
                <Form.Group>
                  <Form.Label>Preis (monatlich, €)</Form.Label>
                  <Form.Control
                    value={price}
                    type={"number"}
                    min={0}
                    step={0.01}
                    onChange={(e) => setPrice(parseFloat(e.target.value))}
                  />
                </Form.Group>
              </Col>
              {pickingMode === PickingModeEnum.Share && (
                <Col>
                  <Form.Group>
                    <Form.Label>Größe (M-Anteil-Equivalent)</Form.Label>
                    <Form.Control
                      value={size}
                      type={"number"}
                      min={0}
                      onChange={(e) => setSize(parseFloat(e.target.value))}
                    />
                  </Form.Group>
                </Col>
              )}
            </Row>
          </ListGroup.Item>
          {pickingMode === PickingModeEnum.Basket && (
            <ListGroup.Item>
              <Table striped hover responsive>
                <thead>
                  <tr>
                    <th>Kistengröße</th>
                    <th>Menge</th>
                  </tr>
                </thead>
                <tbody>
                  {equivalences.map((equivalence, index) => {
                    return (
                      <tr key={equivalence.basketSizeName}>
                        <td>{equivalence.basketSizeName}</td>
                        <td>
                          <Form.Control
                            type={"number"}
                            min={0}
                            step={1}
                            value={equivalence.quantity}
                            onChange={(event) =>
                              onEquivalenceChanged(
                                index,
                                parseInt(event.target.value),
                              )
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </ListGroup.Item>
          )}
        </Form>
      </ListGroup>
    );
  }

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Product verwalten</h5>
      </Modal.Header>
      {getModalBody()}
      <Modal.Footer>
        <TapirButton
          text={"Speichern"}
          icon={"save"}
          variant={"primary"}
          loading={saving}
          onClick={onSave}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default ProductModal;
