import React, { useEffect, useState } from "react";
import { Form, Modal, Spinner } from "react-bootstrap";
import {
  LegalStatusEnum,
  ProductForCancellation,
  SubscriptionsApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import "dayjs/locale/de";
import TapirButton from "../../components/TapirButton.tsx";
import ConfirmModal from "../../components/ConfirmModal.tsx";
import { formatDateText } from "../../utils/formatDateText.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

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
  const [legalStatus, setLegalStatus] = useState<LegalStatusEnum>();
  const [loading, setLoading] = useState(true);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState<
    ProductForCancellation[]
  >([]);
  const [cancelCoopMembershipSelected, setCancelCoopMembershipSelected] =
    useState(false);
  const [confirmationLoading, setConfirmationLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    setSelectedProducts([]);
    setErrors([]);

    if (show) {
      setLoading(true);
      api
        .subscriptionsCancellationDataRetrieve({ memberId: memberId })
        .then((data) => {
          setSubscribedProducts(data.subscribedProducts);
          setCanCancelCoopMembership(data.canCancelCoopMembership);
          setLegalStatus(data.legalStatus);
        })
        .catch(handleRequestError)
        .finally(() => setLoading(false));
    }
  }, [show]);

  function changeSelection(product: ProductForCancellation, selected: boolean) {
    if (selected && !selectedProducts.includes(product)) {
      setSelectedProducts([...selectedProducts, product]);
    } else if (!selected && selectedProducts.includes(product)) {
      setSelectedProducts(
        selectedProducts.filter((p: ProductForCancellation) => p !== product),
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

  function getMembershipText() {
    if (legalStatus === LegalStatusEnum.Association) {
      return "Beitrittserklärung zum Verein";
    }
    return "Beitrittserklärung zur Genossenschaft";
  }

  function buildConfirmationModalText() {
    return (
      <>
        <p>Möchtest du wirklich folgenden Verträge kündigen?</p>
        <ul>
          {selectedProducts.map(
            (productForCancellation: ProductForCancellation) => {
              return (
                <li>
                  {productForCancellation.product.type.name +
                    " (" +
                    productForCancellation.product.name +
                    ") zum " +
                    formatDateText(productForCancellation.cancellationDate)}
                </li>
              );
            },
          )}
          {cancelCoopMembershipSelected && <li>{getMembershipText()}</li>}
        </ul>
      </>
    );
  }

  function onConfirm() {
    setConfirmationLoading(true);
    const productIds = selectedProducts.map(
      (productForCancellation) => productForCancellation.product.id!,
    );
    api
      .subscriptionsCancelSubscriptionsCreate({
        memberId: memberId,
        productIds: productIds,
        cancelCoopMembership: cancelCoopMembershipSelected,
      })
      .then((response) => {
        if (response.subscriptionsCancelled) {
          location.reload();
          return;
        }
        setErrors(response.errors);
      })
      .catch(handleRequestError)
      .finally(() => setConfirmationLoading(false));
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
              {errors.map((error, index) => (
                <div className={"text-danger"} key={index}>
                  {error}
                </div>
              ))}

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
                            subscribedProduct,
                            event.target.checked,
                          )
                        }
                        required={false}
                        checked={selectedProducts.includes(subscribedProduct)}
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
                    label={getMembershipText() + " widerrufen"}
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
            disabled={
              !cancelCoopMembershipSelected && selectedProducts.length === 0
            }
            loading={confirmationLoading}
          />
        </Modal.Footer>
      </Modal>
      <ConfirmModal
        message={buildConfirmationModalText()}
        onCancel={() => setShowConfirmationModal(false)}
        confirmButtonIcon={"contract_delete"}
        confirmButtonText={"Kündigung bestätigen"}
        confirmButtonVariant={"danger"}
        open={showConfirmationModal}
        title={"Verträge kündigen bestätigen"}
        onConfirm={() => {
          onConfirm();
          setShowConfirmationModal(false);
        }}
      />
    </>
  );
};

export default SubscriptionCancellationModal;
