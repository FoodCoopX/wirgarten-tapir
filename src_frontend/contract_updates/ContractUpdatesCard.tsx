import React, { useEffect, useState } from "react";
import { Card, Col, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
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
      .catch(handleRequestError)
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
              <li>
                Zeichnung: {creation.quantity}
                {" × "}
                {creation.product.name} {creation.product.type.name}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionCancellations.map((cancellation) => {
            return (
              <li>
                Kündigung: {cancellation.quantity}
                {" × "}
                {cancellation.product.name} {cancellation.product.type.name}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionChanges.map((change, index) => {
            return (
              <li>
                {change.productType.name}:{" "}
                {change.subscriptionCancellations.map((cancellation) => (
                  <>
                    {cancellation.quantity} {"×"} {cancellation.product.name}
                    {index !== change.subscriptionCancellations.length - 1 &&
                      ", "}
                  </>
                ))}{" "}
                <span className={"material-icons fs-6"}>arrow_forward</span>{" "}
                {change.subscriptionCreations.map((creation, index) => (
                  <>
                    {creation.quantity} {"×"} {creation.product.name}
                    {index !== change.subscriptionCreations.length - 1 && ", "}
                  </>
                ))}
              </li>
            );
          })}
        </ul>
      </>
    );
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
              <h5 className={"mb-0"}>Zeichnungen und Kündigungen</h5>
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
