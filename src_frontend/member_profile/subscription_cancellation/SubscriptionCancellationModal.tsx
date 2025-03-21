import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import {
  Product,
  ProductForCancellation,
  SubscriptionsApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import "dayjs/locale/de";
import TapirButton from "../../components/TapirButton.tsx";
import ConfirmModal from "../../components/ConfirmModal.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";

interface SubscriptionCancellationModalProps {
  onHide: () => void;
  show: boolean;
  memberId: string;
  csrfToken: string;
}

const SubscriptionCancellationModal: React.FC<
  SubscriptionCancellationModalProps
> = ({ onHide, show, memberId, csrfToken }) => {
  const api = useApi(SubscriptionsApi, csrfToken);
  const [subscribedProducts, setSubscribedProducts] = useState<
    ProductForCancellation[]
  >([]);
  const [canCancelCoopMembership, setCanCancelCoopMembership] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState<Product[]>([]);
  const [cancelCoopMembershipSelected, setCancelCoopMembershipSelected] =
    useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .subscriptionsCancellationDataRetrieve({ memberId: memberId })
      .then((test) => {
        setSubscribedProducts(test.subscribedProducts);
        setCanCancelCoopMembership(test.canCancelCoopMembership);
      })
      .catch(alert)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setSelectedProducts([]);
  }, [show]);

  function changeSelection(product: Product, selected: boolean) {
    if (selected && !selectedProducts.includes(product)) {
      setSelectedProducts([...selectedProducts, product]);
    } else if (!selected && selectedProducts.includes(product)) {
      setSelectedProducts(
        selectedProducts.filter((p: Product) => p !== product),
      );
    }
  }

  function getCheckboxLabel(subscribedProduct: ProductForCancellation) {
    let result =
      subscribedProduct.product.type.name +
      " (" +
      subscribedProduct.product.name +
      ") zum " +
      formatDateText(subscribedProduct.cancellationDate) +
      " kündigen";
    if (subscribedProduct.isInTrial) {
      result += " (probezeit)";
    }
    result += ".";
    return result;
  }

  return (
    <>
      <Modal
        onHide={onHide}
        show={show && !showConfirmationModal}
        centered={true}
        size={"lg"}
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <h4>Verträge kündigen</h4>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {loading ? (
            <Spinner />
          ) : (
            <Form
              className={"d-flex flex-column gap-2"}
              id={"subscriptionCancellationModalForm"}
            >
              {subscribedProducts.map(
                (subscribedProduct: ProductForCancellation) => {
                  return (
                    <Form.Group
                      key={subscribedProduct.product.id}
                      controlId={subscribedProduct.product.id}
                    >
                      <Form.Check
                        onChange={(event) =>
                          changeSelection(
                            subscribedProduct.product,
                            event.target.checked,
                          )
                        }
                        required={false}
                        checked={selectedProducts.includes(
                          subscribedProduct.product,
                        )}
                        label={getCheckboxLabel(subscribedProduct)}
                      />
                    </Form.Group>
                  );
                },
              )}
              {canCancelCoopMembership && (
                <Form.Group controlId="cancelCoopMembership">
                  <Form.Check
                    onChange={(event) =>
                      setCancelCoopMembershipSelected(event.target.checked)
                    }
                    required={false}
                    checked={cancelCoopMembershipSelected}
                    label={"Beitrittserklärung zur Genossenschaft widerrufen"}
                  />
                </Form.Group>
              )}
            </Form>
          )}
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"outline-danger"}
            icon={"contract_delete"}
            text={"Verträge kündigen"}
            onClick={() => setShowConfirmationModal(true)}
            disabled={selectedProducts.length === 0}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmModal
        message={"BLABLABLA"}
        onCancel={() => setShowConfirmationModal(false)}
        confirmButtonIcon={"contract_delete"}
        confirmButtonText={"Zum BLABLABLA kündigen"}
        confirmButtonVariant={"danger"}
        open={showConfirmationModal}
        title={"BLABLABLA"}
        onConfirm={() => {
          alert("YOYO");
          setShowConfirmationModal(false);
        }}
      />
    </>
  );
};

export default SubscriptionCancellationModal;
