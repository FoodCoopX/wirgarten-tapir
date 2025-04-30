import React, { useEffect, useState } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { CancelledSubscription, SubscriptionsApi } from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BootstrapPagination from "../components/pagination/BootstrapPagination.tsx";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import TapirButton from "../components/TapirButton.tsx";
import ConfirmModal from "../components/ConfirmModal.tsx";

interface NewContractCancellationsCardProps {
  csrfToken: string;
}

const NewContractCancellationsCard: React.FC<
  NewContractCancellationsCardProps
> = ({ csrfToken }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [subscriptionCount, setSubscriptionCount] = useState(0);
  const [cancelledSubscriptions, setCancelledSubscriptions] = useState<
    CancelledSubscription[]
  >([]);
  const [selectedSubscriptions, setSelectedSubscriptions] = useState<
    CancelledSubscription[]
  >([]);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  useEffect(() => {
    setLoading(true);
    subscriptionsApi
      .subscriptionsApiCancelledSubscriptionsList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
      })
      .then((paginatedResults) => {
        setCancelledSubscriptions(paginatedResults.results);
        setSubscriptionCount(paginatedResults.count);
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }, [currentPage]);

  function onSelectionUpdated(
    checked: boolean,
    selected: CancelledSubscription,
  ) {
    let newSelection;
    if (checked) {
      newSelection = [...selectedSubscriptions, selected];
    } else {
      newSelection = selectedSubscriptions.filter(
        (subscription) => subscription !== selected,
      );
    }
    newSelection.sort(
      (a, b) =>
        a.subscription.cancellationTs!.getTime() -
        b.subscription.cancellationTs!.getTime(),
    );
    setSelectedSubscriptions(newSelection);
  }

  function getConfirmationMessage() {
    return (
      <>
        <p>Möchtest du wirklich folgende Kündigungen als geprüft markieren?</p>
        <ul>
          {Array.from(selectedSubscriptions).map((cancelledSubscription) => (
            <li key={cancelledSubscription.subscription.id}>
              #{cancelledSubscription.member.memberNo}
              {", "}
              {cancelledSubscription.subscription.quantity}
              {" × "}
              {cancelledSubscription.subscription.product.type.name}{" "}
              {cancelledSubscription.subscription.product.name} zum{" "}
              {formatDateNumeric(cancelledSubscription.subscription.endDate)}
            </li>
          ))}
        </ul>
      </>
    );
  }

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex flex-row justify-content-between align-items-center"
                }
              >
                <h5 className={"mb-0"}>Neue Kündigungen</h5>
                <TapirButton
                  variant={"outline-primary"}
                  text={"Ausgewählte Kündigungen geprüft"}
                  icon={"order_approve"}
                  disabled={selectedSubscriptions.length === 0}
                  onClick={() => setShowConfirmModal(true)}
                />
              </div>
            </Card.Header>
            <Card.Body className={"p-0"}>
              <Table striped hover responsive className={"mb-0"}>
                <thead>
                  <tr>
                    <th>Selected</th>
                    <th>Mitgliedsnummer</th>
                    <th>Vorname</th>
                    <th>Nachname</th>
                    <th>Anteilsgröße</th>
                    <th>Verteilort</th>
                    <th>Kündigung zum</th>
                    <th>Gekündigt am</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <PlaceholderTableRows
                      nbRows={DEFAULT_PAGE_SIZE}
                      nbColumns={8}
                      size={"xs"}
                    />
                  ) : (
                    cancelledSubscriptions.map((cancelledSubscription) => {
                      return (
                        <tr
                          key={cancelledSubscription.subscription.id}
                          className={
                            selectedSubscriptions.includes(
                              cancelledSubscription,
                            )
                              ? "table-primary"
                              : ""
                          }
                          onClick={() =>
                            onSelectionUpdated(
                              !selectedSubscriptions.includes(
                                cancelledSubscription,
                              ),
                              cancelledSubscription,
                            )
                          }
                          style={{ cursor: "pointer" }}
                        >
                          <td>
                            <input
                              type={"checkbox"}
                              checked={selectedSubscriptions.includes(
                                cancelledSubscription,
                              )}
                              onChange={(event) =>
                                onSelectionUpdated(
                                  event.target.checked,
                                  cancelledSubscription,
                                )
                              }
                            />
                          </td>
                          <td>{cancelledSubscription.member.memberNo}</td>
                          <td>{cancelledSubscription.member.firstName}</td>
                          <td>{cancelledSubscription.member.lastName}</td>
                          <td>
                            {cancelledSubscription.subscription.quantity}
                            {" × "}
                            {
                              cancelledSubscription.subscription.product.type
                                .name
                            }{" "}
                            {cancelledSubscription.subscription.product.name}
                          </td>
                          <td>{cancelledSubscription.pickupLocation.name}</td>
                          <td>
                            {formatDateNumeric(
                              cancelledSubscription.subscription.endDate,
                            )}
                          </td>
                          <td>
                            {formatDateNumeric(
                              cancelledSubscription.subscription.cancellationTs,
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </Table>
            </Card.Body>
            {subscriptionCount > DEFAULT_PAGE_SIZE && (
              <Card.Footer className="d-flex justify-content-center align-items-center">
                <BootstrapPagination
                  currentPage={currentPage}
                  pageSize={DEFAULT_PAGE_SIZE}
                  itemCount={subscriptionCount}
                  goToPage={setCurrentPage}
                />
              </Card.Footer>
            )}
          </Card>
        </Col>
      </Row>
      <ConfirmModal
        onCancel={() => setShowConfirmModal(false)}
        confirmButtonIcon={"order_approve"}
        confirmButtonText={"Bestätigen"}
        message={getConfirmationMessage()}
        onConfirm={() => alert("TODO")}
        confirmButtonVariant={"primary"}
        open={showConfirmModal}
        title={"Prüfung bestätigen"}
      />
    </>
  );
};

export default NewContractCancellationsCard;
