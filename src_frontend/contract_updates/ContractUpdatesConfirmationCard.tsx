import React, { useState } from "react";
import { Modal } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import {
  MemberDataToConfirm,
  Subscription,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import formatSubscription from "../utils/formatSubscription.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface ContractUpdatesConfirmationCardProps {
  csrfToken: string;
  changes: MemberDataToConfirm;
  show: boolean;
  onHide: () => void;
  onConfirmed: () => void;
}

const ContractUpdatesConfirmationCard: React.FC<
  ContractUpdatesConfirmationCardProps
> = ({ csrfToken, changes, show, onHide, onConfirmed }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(false);

  function buildCancellations(
    cancellations: Subscription[],
    showCancellationType: boolean,
  ) {
    return (
      <ul>
        {cancellations.map((cancellation, index) => {
          return (
            <li>
              {formatSubscription(cancellation)}, Vertrag endet am{" "}
              {formatDateNumeric(cancellation.endDate)}{" "}
              {showCancellationType &&
                "(" + changes.cancellationTypes[index] + ")"}
            </li>
          );
        })}
      </ul>
    );
  }

  function buildCreations(creations: Subscription[]) {
    return (
      <ul>
        {creations.map((creation) => {
          return (
            <li>
              {formatSubscription(creation)}, Vertrag startet am{" "}
              {formatDateNumeric(creation.startDate)}
            </li>
          );
        })}
      </ul>
    );
  }

  function onConfirm() {
    setLoading(true);

    const confirmCreationIds = changes.subscriptionCreations.map(
      (subscriptions) => subscriptions.id!,
    );
    for (const change of changes.subscriptionChanges) {
      confirmCreationIds.push(
        ...change.subscriptionCreations.map((subscription) => subscription.id!),
      );
    }

    const confirmCancellationIds = changes.subscriptionCancellations.map(
      (subscriptions) => subscriptions.id!,
    );
    for (const change of changes.subscriptionChanges) {
      confirmCancellationIds.push(
        ...change.subscriptionCancellations.map(
          (subscription) => subscription.id!,
        ),
      );
    }
    subscriptionsApi
      .subscriptionsApiConfirmSubscriptionChangesCreate({
        confirmCreationIds: confirmCreationIds,
        confirmCancellationIds: confirmCancellationIds,
      })
      .then(onConfirmed)
      .catch(handleRequestError)
      .finally(() => setLoading(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>
          Änderung bestätigen: {changes.member.firstName}{" "}
          {changes.member.lastName} #{changes.member.memberNo}
        </h5>
      </Modal.Header>
      <Modal.Body>
        <p>
          Mitglied{" "}
          <a href={changes.memberProfileUrl}>
            {changes.member.firstName} {changes.member.lastName} #
            {changes.member.memberNo}
          </a>{" "}
          hat folgende Änderungen gefordert:
        </p>
        {changes.subscriptionCreations.length > 0 && (
          <>
            <h6>Neue Zeichnungen</h6>
            {buildCreations(changes.subscriptionCreations)}
          </>
        )}
        {changes.subscriptionCancellations.length > 0 && (
          <>
            <h6>
              Neue Kündigungen{" "}
              {changes.showWarning && (
                <span className={"material-icons text-warning"}>warning</span>
              )}
            </h6>
            {buildCancellations(changes.subscriptionCancellations, true)}
          </>
        )}
        {changes.subscriptionChanges.length > 0 && (
          <>
            <h6>Vertragsänderungen</h6>
            <ul>
              {changes.subscriptionChanges.map((update) => {
                return (
                  <>
                    {update.productType.name}
                    {buildCancellations(
                      update.subscriptionCancellations,
                      false,
                    )}
                    {buildCreations(update.subscriptionCreations)}
                  </>
                );
              })}
            </ul>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Bestätigen"}
          variant={"primary"}
          loading={loading}
          onClick={onConfirm}
          icon={"contract_edit"}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default ContractUpdatesConfirmationCard;
