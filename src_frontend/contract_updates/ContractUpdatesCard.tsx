import React, { useEffect, useState } from "react";
import { Badge, Card, Col, Form, ListGroup, Row, Table } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { MemberDataToConfirm, type SubscriptionChange, SubscriptionsApi } from "../api-client";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { ToastData } from "../types/ToastData.ts";
import ConfirmRevokeModal from "./ConfirmRevokeModal.tsx";
import { getMinimumDate } from "../utils/getMinimumDate.ts";

interface ContractUpdatesCardProps {
  csrfToken: string;
}

type ContractFilter = "all" | "includes_creations" | "includes_cancellations";

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
  const [selectedFilter, setSelectedFilter] = useState<ContractFilter>("all");
  const [showRevokeConfirmModal, setShowRevokeConfirmModal] = useState(false);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    setLoading(true);

    loadList();
  }, []);

  useEffect(() => {
    setSelectedChanges(new Set());
  }, [selectedFilter]);

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
          "Fehler beim Laden der Zeichnungen",
          setToastDatas,
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
              <li
                key={creation.id}
                className={creation.autoConfirmed ? "text-warning" : ""}
              >
                Zeichnung: {creation.quantity}
                {" × "}
                {creation.product.name} {creation.product.type.name} am{" "}
                {formatDateNumeric(creation.startDate)}
                {creation.autoConfirmed
                  ? " (automatische Bestätigung schon versendet)"
                  : ""}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionCancellations.map((cancellation) => {
            return (
              <li key={cancellation.id}>
                Kündigung: {cancellation.quantity}
                {" × "}
                {cancellation.product.name} {cancellation.product.type.name} zum{" "}
                {formatDateNumeric(cancellation.endDate)}
              </li>
            );
          })}
          {memberDataToConfirm.subscriptionsDeleted.map((deleted) => {
            return (
              <li key={deleted.id}>
                Kündigung am {formatDateNumeric(deleted.createdDate)} vor
                Vertragsstart: <br />
                {deleted.subscriptions}
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
                  <span
                    key={creation.id}
                    className={creation.autoConfirmed ? "text-warning" : ""}
                  >
                    {creation.quantity} {"×"} {creation.product.name}
                    {" ("}
                    {formatDateNumeric(creation.startDate)}
                    {") "}
                    {creation.autoConfirmed
                      ? " (automatische Bestätigung schon versendet)"
                      : ""}
                    {index !== change.subscriptionCreations.length - 1 && ", "}
                  </span>
                ))}
              </li>
            );
          })}
          {memberDataToConfirm.sharePurchases.map((purchase) => (
            <li className={purchase.autoConfirmed ? "text-warning" : ""}>
              {purchase.quantity}{" "}
              {purchase.quantity === 1
                ? "Genossenschaftsanteil"
                : "Genossenschaftsanteile"}{" "}
              gültig am {formatDateNumeric(purchase.validAt)}
              {purchase.autoConfirmed
                ? " (automatische Bestätigung schon versendet)"
                : ""}
            </li>
          ))}
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

    if ("sharePurchases" in data) {
      dates = [
        ...dates,
        ...data.sharePurchases.map((purchase) => purchase.validAt),
      ];
    }

    if ("subscriptionsDeleted" in data) {
      {
        dates = [
          ...dates,
          ...data.subscriptionsDeleted.map((deleted) => deleted.createdDate),
        ];
      }
    }

    if (dates.length === 0) {
      return new Date();
    }

    return getMinimumDate(dates);
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
      .catch((error) =>
        handleRequestError(error, "Fehler beim Bestätigen", setToastDatas),
      )
      .finally(() => setLoading(false));
  }

  function isAtLeastOneCancellationSelected() {
    for (const change of selectedChanges) {
      if (change.subscriptionCancellations.length > 0) {
        return true;
      }
    }
    return false;
  }

  function onConfirmRevoke(putOnWaitingList: boolean) {
    if (isAtLeastOneCancellationSelected()) {
      alert("Kündigungen können nicht widerrufen werden.");
      return;
    }

    setLoading(true);

    let coopSharePurchaseIds: string[] = [];
    for (const change of selectedChanges) {
      coopSharePurchaseIds.push(
        ...change.sharePurchases.map((purchase) => purchase.id!),
      );
    }

    subscriptionsApi
      .subscriptionsApiRevokeChangesCreate({
        subscriptionCreationIds: getCreationIdsToConfirm(),
        coopSharePurchaseIds: coopSharePurchaseIds,
        putOnWaitingList: putOnWaitingList,
      })
      .then(() => {
        setConfirmedChanges(new Set(selectedChanges));
        setSelectedChanges(new Set());
        loadList();
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Widerrufen", setToastDatas),
      )
      .finally(() => {
        setLoading(false);
        setShowRevokeConfirmModal(false);
      });
  }

  function getFilteredChanges(filter?: ContractFilter) {
    if (filter === undefined) {
      filter = selectedFilter;
    }
    switch (filter) {
      case "all":
        return changesToConfirm;
      case "includes_cancellations":
        return changesToConfirm.filter((change) =>
          doesChangeHaveCancellations(change),
        );
      case "includes_creations":
        return changesToConfirm.filter((change) =>
          doesChangeHaveCreations(change),
        );
    }
  }

  function doesChangeHaveCreations(change: MemberDataToConfirm) {
    return (
      change.subscriptionCreations.length > 0 ||
      change.subscriptionChanges.length > 0 ||
      change.sharePurchases.length > 0
    );
  }

  function doesChangeHaveCancellations(change: MemberDataToConfirm) {
    return change.subscriptionCancellations.length > 0;
  }

  function doesSelectionContainChangesThatAreAlreadyValid(): boolean {
    for (const memberChanges of selectedChanges) {
      if (getEarliestChange(memberChanges) <= new Date()) {
        return true;
      }
    }

    return false;
  }

  function getRevokeButtonText() {
    if (doesSelectionContainChangesThatAreAlreadyValid()) {
      return "Nur zukünftige Zeichnungen können widerrufen werden";
    }

    const base = "Auswahl widerrufen";
    if (selectedChanges.size === 0) {
      return base;
    }

    return base + " (" + selectedChanges.size + ")";
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
                <div className={"d-flex flex-row gap-2"}>
                  <TapirButton
                    text={getRevokeButtonText()}
                    disabled={
                      selectedChanges.size === 0 ||
                      doesSelectionContainChangesThatAreAlreadyValid()
                    }
                    icon={"contract_delete"}
                    variant={"outline-danger"}
                    onClick={() => setShowRevokeConfirmModal(true)}
                    loading={loading}
                  />
                  <TapirButton
                    text={
                      "Auswahl bestätigen" +
                      (selectedChanges.size > 0
                        ? " (" + selectedChanges.size + ")"
                        : "")
                    }
                    disabled={selectedChanges.size === 0}
                    icon={"check"}
                    variant={"primary"}
                    onClick={onConfirm}
                    loading={loading}
                  />
                </div>
              </div>
            </Card.Header>
            <ListGroup>
              <ListGroup.Item>
                <div>
                  {["all", "includes_creations", "includes_cancellations"].map(
                    (filter) => (
                      <Form.Check id={filter} name={"filter"} key={filter}>
                        <Form.Check.Input
                          type={"radio"}
                          checked={filter === selectedFilter}
                          onChange={(event) => {
                            if (event.target.checked) {
                              setSelectedFilter(filter as ContractFilter);
                            }
                          }}
                        />
                        <Form.Check.Label>
                          <span>
                            {filter === "all"
                              ? "Alles Anzeigen"
                              : filter === "includes_creations"
                                ? "Nur Zeichnungen anzeigen"
                                : "Nur Kündigungen Anzeigen"}{" "}
                          </span>
                          <Badge>
                            {
                              getFilteredChanges(filter as ContractFilter)
                                .length
                            }
                          </Badge>
                        </Form.Check.Label>
                      </Form.Check>
                    ),
                  )}
                </div>
              </ListGroup.Item>
              <ListGroup.Item className={"p-0"}>
                <Table striped hover responsive className={"mb-0"}>
                  <thead>
                    <tr>
                      <th>
                        <Form.Check
                          checked={
                            selectedChanges.size === changesToConfirm.length
                          }
                          onClick={() => {
                            if (
                              selectedChanges.size === changesToConfirm.length
                            ) {
                              setSelectedChanges(new Set());
                            } else {
                              setSelectedChanges(new Set(changesToConfirm));
                            }
                          }}
                        />
                      </th>
                      <th>Mitglied</th>
                      <th>Verteilort</th>
                      <th>Änderungen</th>
                      <th>Gültig ab</th>
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
                      getFilteredChanges().map((change) => {
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
                                {change.member.firstName}{" "}
                                {change.member.lastName} #
                                {change.member.memberNo}
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
              </ListGroup.Item>
            </ListGroup>
          </Card>
        </Col>
      </Row>
      <ConfirmRevokeModal
        open={showRevokeConfirmModal}
        onRevoke={() => onConfirmRevoke(false)}
        onWaitingList={() => onConfirmRevoke(true)}
        onCancel={() => setShowRevokeConfirmModal(false)}
        selectedChanges={selectedChanges}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default ContractUpdatesCard;
