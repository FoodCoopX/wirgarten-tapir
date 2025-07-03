import React, { useEffect, useState } from "react";
import { Badge, Card, Col, Form, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  CoopShareTransaction,
  MemberDataToConfirm,
  type SubscriptionChange,
  SubscriptionsApi,
} from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import TapirButton from "../components/TapirButton.tsx";

interface ContractUpdatesCardProps {
  csrfToken: string;
}

const ContractUpdatesCard: React.FC<ContractUpdatesCardProps> = ({
  csrfToken,
}) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [changesToConfirm, setChangesToConfirm] = useState<
    MemberDataToConfirm[]
  >([]);
  const [selectedChanges, setSelectedChanges] = useState<
    Set<MemberDataToConfirm>
  >(new Set());
  const [confirmedChanges, setConfirmedChanges] = useState<
    Set<MemberDataToConfirm>
  >(new Set());

  useEffect(() => {
    setLoading(true);

    loadList();
  }, []);

  function loadList() {
    subscriptionsApi
      .subscriptionsApiMemberDataToConfirmList()
      .then((changes) => {
        changes.sort(
          (a, b) =>
            getEarliestChange(a).getTime() - getEarliestChange(b).getTime(),
        );
        setChangesToConfirm(changes);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Zeichnungen: " + error.message,
        ),
      )
      .finally(() => setLoading(false));
  }

  function buildChanges(memberDataToConfirm: MemberDataToConfirm) {
    return (
      <>
        {memberDataToConfirm.showWarning && (
          <span className={"material-icons text-warning"}>warning</span>
        )}
        <ul>
          {memberDataToConfirm.subscriptionCreations.map((creation) => {
            return (
              <li key={creation.id}>
                Zeichnung: {creation.quantity}
                {" × "}
                {creation.product.name} {creation.product.type.name} am{" "}
                {formatDateNumeric(creation.startDate)}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionCancellations.map((cancellation) => {
            return (
              <li key={cancellation.id}>
                Kündigung: {cancellation.quantity}
                {" × "}
                {cancellation.product.name} {cancellation.product.type.name}am{" "}
                {formatDateNumeric(cancellation.endDate)}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionChanges.map((change, index) => {
            return (
              <li key={index}>
                {change.productType.name}:{" "}
                {change.subscriptionCancellations.map((cancellation) => (
                  <span key={cancellation.id}>
                    {cancellation.quantity} {"×"} {cancellation.product.name}
                    {index !== change.subscriptionCancellations.length - 1 &&
                      ", "}
                  </span>
                ))}{" "}
                <span className={"material-icons fs-6"}>arrow_forward</span>{" "}
                {change.subscriptionCreations.map((creation, index) => (
                  <span key={creation.id}>
                    {creation.quantity} {"×"} {creation.product.name}
                    {index !== change.subscriptionCreations.length - 1 && ", "}
                  </span>
                ))}
              </li>
            );
          })}
          {getNumberOfSharesPurchased(memberDataToConfirm.sharePurchases) ===
            1 && (
            <li>
              1 Genossenschaftsanteil gültig am{" "}
              {formatDateNumeric(memberDataToConfirm.sharePurchases[0].validAt)}
            </li>
          )}
          {getNumberOfSharesPurchased(memberDataToConfirm.sharePurchases) >
            1 && (
            <li>
              {getNumberOfSharesPurchased(memberDataToConfirm.sharePurchases)}{" "}
              Genossenschaftsanteile gültig am{" "}
              {formatDateNumeric(memberDataToConfirm.sharePurchases[0].validAt)}
            </li>
          )}
        </ul>
      </>
    );
  }

  function getNumberOfSharesPurchased(purchases: CoopShareTransaction[]) {
    return purchases.reduce((sum, purchase) => sum + purchase.quantity, 0);
  }

  function getEarliestChange(data: MemberDataToConfirm | SubscriptionChange) {
    let dates = [
      ...data.subscriptionCreations.map((creation) => creation.startDate!),
      ...data.subscriptionCancellations.map(
        (cancellation) => cancellation.endDate!,
      ),
    ];
    if ("subscriptionChanges" in data) {
      dates = [...dates, ...data.subscriptionChanges.map(getEarliestChange)];
    }

    return dates.reduce(function (a, b) {
      return a < b ? a : b;
    }, new Date());
  }

  function getCreationIdsToConfirm() {
    const ids = [];
    for (const change of selectedChanges) {
      ids.push(
        ...change.subscriptionCreations.map(
          (subscriptions) => subscriptions.id!,
        ),
      );
      for (const temp of change.subscriptionChanges) {
        ids.push(
          ...temp.subscriptionCreations.map((subscription) => subscription.id!),
        );
      }
    }
    return ids;
  }

  function getCancellationIdsToConfirm() {
    const ids = [];
    for (const change of selectedChanges) {
      ids.push(
        ...change.subscriptionCancellations.map(
          (subscriptions) => subscriptions.id!,
        ),
      );
      for (const temp of change.subscriptionChanges) {
        ids.push(
          ...temp.subscriptionCancellations.map(
            (subscription) => subscription.id!,
          ),
        );
      }
    }
    return ids;
  }

  function getSharePurchaseIdsToConfirm() {
    const ids = [];
    for (const change of selectedChanges) {
      ids.push(...change.sharePurchases.map((purchase) => purchase.id!));
    }
    return ids;
  }

  function onConfirm() {
    setLoading(true);

    subscriptionsApi
      .subscriptionsApiConfirmSubscriptionChangesCreate({
        confirmCreationIds: getCreationIdsToConfirm(),
        confirmCancellationIds: getCancellationIdsToConfirm(),
        confirmPurchaseIds: getSharePurchaseIdsToConfirm(),
      })
      .then(() => {
        setConfirmedChanges(new Set(selectedChanges));
        setSelectedChanges(new Set());
        loadList();
      })
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex flex-row align-items-center justify-content-between"
                }
              >
                <h5 className={"mb-0"}>
                  Zeichnungen und Kündigungen{" "}
                  <Badge>{changesToConfirm.length}</Badge>
                </h5>
                <TapirButton
                  text={"Auswahl bestätigen"}
                  disabled={selectedChanges.size === 0}
                  icon={"check"}
                  variant={"primary"}
                  onClick={onConfirm}
                  loading={loading}
                />
              </div>
            </Card.Header>
            <Card.Body className={"p-0"}>
              <Table striped hover responsive className={"mb-0"}>
                <thead>
                  <tr>
                    <th></th>
                    <th>Mitglied</th>
                    <th>Verteilort</th>
                    <th>Änderungen</th>
                    <th>Datum</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <PlaceholderTableRows
                      nbRows={DEFAULT_PAGE_SIZE}
                      nbColumns={6}
                      size={"lg"}
                    />
                  ) : (
                    changesToConfirm.map((change) => {
                      if (confirmedChanges.has(change)) {
                        return (
                          <PlaceholderTableRows
                            nbRows={1}
                            nbColumns={6}
                            size={"lg"}
                          />
                        );
                      }

                      return (
                        <tr
                          key={change.member.id}
                          onClick={() =>
                            setSelectedChanges((selected) => {
                              if (selected.has(change)) {
                                selected.delete(change);
                              } else {
                                selected.add(change);
                              }

                              return new Set(selected);
                            })
                          }
                          style={{ cursor: "pointer" }}
                          className={
                            selectedChanges.has(change) ? "table-primary" : ""
                          }
                        >
                          <td>
                            <Form.Check
                              checked={selectedChanges.has(change)}
                              readOnly={true}
                            />
                          </td>
                          <td>
                            <a href={change.memberProfileUrl}>
                              {change.member.firstName} {change.member.lastName}{" "}
                              #{change.member.memberNo}
                            </a>
                          </td>
                          <td>{change.pickupLocation?.name}</td>
                          <td>{buildChanges(change)}</td>
                          <td>
                            {formatDateNumeric(getEarliestChange(change))}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default ContractUpdatesCard;
