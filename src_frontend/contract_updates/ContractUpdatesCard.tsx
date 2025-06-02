import React, { useEffect, useState } from "react";
import { Badge, Card, Col, Row, Table } from "react-bootstrap";
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
import ContractUpdatesConfirmationModal from "./ContractUpdatesConfirmationCard.tsx";

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
  const [selectedChange, setSelectedChange] = useState<MemberDataToConfirm>();
  const [confirmedChange, setConfirmedChange] = useState<MemberDataToConfirm>();

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

  function onConfirmed() {
    setConfirmedChange(selectedChange);
    setSelectedChange(undefined);
    loadList();
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
                {creation.product.name} {creation.product.type.name}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionCancellations.map((cancellation) => {
            return (
              <li key={cancellation.id}>
                Kündigung: {cancellation.quantity}
                {" × "}
                {cancellation.product.name} {cancellation.product.type.name}
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
            1 && <li>1 Genossenschaftsanteil</li>}
          {getNumberOfSharesPurchased(memberDataToConfirm.sharePurchases) >
            1 && (
            <li>
              {getNumberOfSharesPurchased(memberDataToConfirm.sharePurchases)}{" "}
              Genossenschaftsanteile
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

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <h5 className={"mb-0"}>
                Zeichnungen und Kündigungen{" "}
                <Badge>{changesToConfirm.length}</Badge>
              </h5>
            </Card.Header>
            <Card.Body className={"p-0"}>
              <Table striped hover responsive className={"mb-0"}>
                <thead>
                  <tr>
                    <th>Mitgliedsnummer</th>
                    <th>Vorname</th>
                    <th>Nachname</th>
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
                      if (change == confirmedChange) {
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
                          onClick={() => setSelectedChange(change)}
                          style={{ cursor: "pointer" }}
                        >
                          <td>{change.member.memberNo}</td>
                          <td>{change.member.firstName}</td>
                          <td>{change.member.lastName}</td>
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
      {selectedChange && (
        <ContractUpdatesConfirmationModal
          csrfToken={csrfToken}
          changes={selectedChange}
          show={true}
          onHide={() => setSelectedChange(undefined)}
          onConfirmed={onConfirmed}
        />
      )}
    </>
  );
};

export default ContractUpdatesCard;
