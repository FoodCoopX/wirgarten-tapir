import React, { useEffect, useState } from "react";
import { Alert, Form, ListGroup, Modal, Spinner } from "react-bootstrap";
import {
  ActionEnum,
  SubscriptionsApiConvertWeekToDateForSubscriptionChangeRetrieveBoundaryEnum as Boundary,
  CoopApi,
  Member,
  PublicSubscription,
  RenewalCancellationStatusEnum,
  SolidarityContribution,
  SolidarityContributionApi,
  Subscription,
  SubscriptionDetails,
  SubscriptionsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { toApiDate } from "../utils/apiDate.ts";
import { formatCurrency } from "../utils/formatCurrency.ts";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";
import formatSubscription, {
  formatPublicSubscription,
} from "../utils/formatSubscription.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import SubscriptionChangeDatePicker from "./SubscriptionChangeDatePicker.tsx";

interface SubscriptionChangeDatesModalProps {
  onHide: () => void;
  show: boolean;
  subscriptionId: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

interface Choice {
  action: ActionEnum;
  date?: Date;
}

const HEADER_HELP_TEXT = (
  <>
    <p>
      Du kannst hier die Vertragslaufzeiten anpassen, z.B. zum Eintragen von
      Kulanzkündigungen während der Vertragsperiode.
    </p>
    <p>
      Eine KW steht beim Vertragsbeginn für den Montag, beim Vertragsende für
      den Sonntag. Der erste und der letzte Tag der Vertragsperiode können
      unabhängig vom Wochentag gewählt werden.
    </p>
    <p>
      Bitte prüft nach Veränderungen der Vertragslaufzeiten anschließend die
      Zahlungsreihe für das bearbeitete Mitglied. Es ergeben sich ggf.
      Rückzahlungen, z.B. wenn vierteljährlich, halbjährlich oder jährlich
      gezahlt wird und somit längere Perioden vorbezahlt wurden.
    </p>
    <p>
      Das Mitglied erhält keine automatisierte E-Mail nach Einstellung der neuen
      Vertragsdaten.
    </p>
  </>
);

const OTHER_CONTRACTS_HELP_TEXT = (
  <>
    <p>
      Verträge und Solidarbeiträge, die am neuen Vertragsende noch laufen,
      bekommen das gleiche Vertragsende und werden nicht verlängert.
    </p>
    <p>Früher endende Verträge und Solidarbeiträge werden nicht geändert.</p>
    <p>
      Solidarbeiträge, die nach dem neuen Vertragsende beginnen, werden
      gelöscht. Verträge, die nach dem neuen Vertragsende beginnen, müssen
      separat angepasst werden.
    </p>
    <p>
      Je nachdem, ob das Mitglied schon vorbezahlt hat, können Gutschriften
      entstehen.
    </p>
  </>
);

const SubscriptionChangeDatesModal: React.FC<
  SubscriptionChangeDatesModalProps
> = ({ onHide, show, subscriptionId, setToastDatas }) => {
  const subscriptionsApi = useApi(SubscriptionsApi);
  const solidarityContributionApi = useApi(SolidarityContributionApi);
  const coopApi = useApi(CoopApi);
  const [mainDataLoading, setMainDataLoading] = useState(true);
  const [extraDataLoading, setExtraDataLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionDetails>();
  const [memberData, setMemberData] = useState<Member>();
  const [choice, setChoice] = useState<Choice>();
  const [error, setError] = useState<string>();
  const [solidarityContributions, setSolidarityContributions] = useState<
    SolidarityContribution[]
  >([]);
  const [updateOtherContracts, setUpdateOtherContracts] = useState(false);
  const [otherSubscriptions, setOtherSubscriptions] = useState<
    PublicSubscription[]
  >([]);

  useEffect(() => {
    if (!show) {
      return;
    }

    setMainDataLoading(true);
    setChoice(undefined);
    setError(undefined);
    setUpdateOtherContracts(false);

    subscriptionsApi
      .subscriptionsSubscriptionsRetrieve({ id: subscriptionId })
      .then(setSubscription)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Vertragsdaten",
          setToastDatas,
        ),
      )
      .finally(() => setMainDataLoading(false));
  }, [show]);

  useEffect(() => {
    if (!show || !subscription) {
      return;
    }

    setExtraDataLoading(true);

    Promise.all([
      coopApi.coopMembersRetrieve({ id: subscription.member }),
      subscriptionsApi.subscriptionsApiMemberSubscriptionDataRetrieve({
        memberId: subscription.member,
      }),
      solidarityContributionApi.solidarityContributionApiMemberSolidarityContributionsRetrieve(
        { memberId: subscription.member },
      ),
    ])
      .then(([memberData, subscriptionData, solidarityData]) => {
        setMemberData(memberData);
        setOtherSubscriptions(
          subscriptionData.subscriptions
            .filter(
              (otherSubscription) =>
                otherSubscription.productId !== subscription.product.id,
            )
            .sort((a, b) => a.startDate.localeCompare(b.startDate)),
        );
        setSolidarityContributions(solidarityData.contributions);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der zusätzlichen Daten",
          setToastDatas,
        ),
      )
      .finally(() => setExtraDataLoading(false));
  }, [subscription, show]);

  function selectAction(action: ActionEnum) {
    setChoice({ action: action });
    setError(undefined);
    if (action === ActionEnum.ChangeStart) {
      setUpdateOtherContracts(false);
    }
  }

  function dateIsUnchanged() {
    if (!subscription || !choice?.date) {
      return false;
    }
    const currentDate =
      choice.action === ActionEnum.ChangeStart
        ? subscription.startDate
        : subscription.endDate;
    return toApiDate(choice.date) === currentDate;
  }

  function canSave() {
    if (!choice) {
      return false;
    }
    if (choice.action === ActionEnum.CancelRenewal) {
      return (
        subscription?.renewalCancellationStatus ===
        RenewalCancellationStatusEnum.Available
      );
    }
    return choice.date !== undefined && !dateIsUnchanged();
  }

  function onConfirmChange() {
    if (!choice || !canSave()) {
      return;
    }

    setMainDataLoading(true);

    subscriptionsApi
      .subscriptionsApiDatesChangeCreate({
        subscriptionDateChangeRequestRequest: {
          subscriptionId: subscriptionId,
          action: choice.action,
          date: choice.date ? toApiDate(choice.date) : undefined,
          updateOtherContracts: updateOtherContracts,
        },
      })
      .then((response) => {
        if (response.orderConfirmed) {
          location.reload();
          onHide();
        } else {
          setError(response.error ?? undefined);
        }
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Ändern der Vertragsdaten",
          setToastDatas,
        ),
      )
      .finally(() => setMainDataLoading(false));
  }

  function getRenewalDescription(subscription: SubscriptionDetails) {
    if (subscription.renewalStartDate) {
      return `Die Verlängerung ab dem ${formatDateNumeric(subscription.renewalStartDate)} wird gelöscht.`;
    }
    return "Der Vertrag wird nicht verlängert.";
  }

  function getMainSummaryLines(
    subscription: SubscriptionDetails,
    choice: Choice,
    endDate: string,
  ): string[] {
    switch (choice.action) {
      case ActionEnum.ChangeStart:
        return [`Neuer Vertragsbeginn: ${formatDateNumeric(choice.date!)}`];
      case ActionEnum.ChangeEnd:
        return [
          `Neues Vertragsende: ${endDate}`,
          getRenewalDescription(subscription),
        ];
      case ActionEnum.CancelRenewal:
        return [
          `Der Vertrag läuft bis zum ${endDate} und wird als gekündigt markiert.`,
          getRenewalDescription(subscription),
        ];
    }
  }

  function getSummaryLines(subscription: SubscriptionDetails): string[] {
    if (!choice) {
      return [];
    }

    if (choice.action !== ActionEnum.CancelRenewal) {
      if (!choice.date) {
        return [];
      }
      if (dateIsUnchanged()) {
        return ["Das gewählte Datum entspricht dem aktuellen Datum."];
      }
    }

    const endDate = formatDateNumeric(
      choice.action === ActionEnum.ChangeEnd && choice.date
        ? choice.date
        : subscription.endDate,
    );

    const lines = getMainSummaryLines(subscription, choice, endDate);
    if (updateOtherContracts) {
      if (getAffectedOtherSubscriptions(subscription).length > 0) {
        lines.push(
          `Weitere Verträge enden ebenfalls am ${endDate} und werden nicht verlängert, spätere Verträge werden gelöscht.`,
        );
      }
      if (solidarityContributions.length > 0) {
        lines.push(
          `Der Solidarbeitrag endet am ${endDate}, spätere Solidarbeiträge werden gelöscht.`,
        );
      }
    }
    if (choice.action !== ActionEnum.CancelRenewal || updateOtherContracts) {
      lines.push(
        "Je nach Zahlungsrhythmus können Gutschriften entstehen: bitte die Zahlungsreihe des Mitglieds prüfen.",
      );
    }
    return lines;
  }

  function getDatePicker(
    subscription: SubscriptionDetails,
    action: ActionEnum,
    boundary: Boundary,
  ) {
    return (
      <div className={"ms-4 mb-2"}>
        <SubscriptionChangeDatePicker
          subscriptionId={subscriptionId}
          subscription={subscription}
          boundary={boundary}
          onChange={(date) => setChoice({ action: action, date: date })}
          setToastDatas={setToastDatas}
        />
      </div>
    );
  }

  function getActionChoice(subscription: SubscriptionDetails) {
    const renewalStatus = subscription.renewalCancellationStatus;
    return (
      <Form.Group>
        <Form.Check
          type={"radio"}
          id={"action_change_end"}
          name={"action"}
          label={"Vertragsende ändern (Sonderkündigung)"}
          checked={choice?.action === ActionEnum.ChangeEnd}
          onChange={() => selectAction(ActionEnum.ChangeEnd)}
        />
        {choice?.action === ActionEnum.ChangeEnd &&
          getDatePicker(subscription, ActionEnum.ChangeEnd, Boundary.End)}
        {renewalStatus !== RenewalCancellationStatusEnum.NotAvailable && (
          <Form.Check
            type={"radio"}
            id={"action_cancel_renewal"}
            name={"action"}
            label={`Zum Vertragsende kündigen (${formatDateNumeric(subscription.endDate)})`}
            disabled={
              renewalStatus ===
              RenewalCancellationStatusEnum.BeforeNoticePeriodEnd
            }
            checked={choice?.action === ActionEnum.CancelRenewal}
            onChange={() => selectAction(ActionEnum.CancelRenewal)}
          />
        )}
        {renewalStatus ===
          RenewalCancellationStatusEnum.BeforeNoticePeriodEnd && (
          <Alert variant={"warning"} className={"ms-4 mb-2"}>
            Die Kündigungsfrist ist noch nicht abgelaufen. Kündigungen zum Ende
            der Vertragsperiode bitte über das Mitgliederprofil eintragen.
          </Alert>
        )}
        <Form.Check
          type={"radio"}
          id={"action_change_start"}
          name={"action"}
          label={"Vertragsbeginn ändern"}
          checked={choice?.action === ActionEnum.ChangeStart}
          onChange={() => selectAction(ActionEnum.ChangeStart)}
        />
        {choice?.action === ActionEnum.ChangeStart &&
          getDatePicker(subscription, ActionEnum.ChangeStart, Boundary.Start)}
      </Form.Group>
    );
  }

  function getAffectedOtherSubscriptions(subscription: SubscriptionDetails) {
    const newEndDate =
      choice?.action === ActionEnum.ChangeEnd && choice.date
        ? toApiDate(choice.date)
        : subscription.endDate;
    const rangeEnd =
      newEndDate > subscription.endDate ? newEndDate : subscription.endDate;
    return otherSubscriptions.filter(
      (otherSubscription) =>
        otherSubscription.startDate <= rangeEnd &&
        otherSubscription.endDate >= newEndDate,
    );
  }

  function getOtherContracts(subscription: SubscriptionDetails) {
    if (extraDataLoading) {
      return <Spinner />;
    }

    const affectedOtherSubscriptions =
      getAffectedOtherSubscriptions(subscription);
    if (
      affectedOtherSubscriptions.length + solidarityContributions.length ===
      0
    ) {
      return null;
    }

    return (
      <>
        <Form.Check
          id={"update_other_contracts"}
          checked={updateOtherContracts}
          onChange={(e) => setUpdateOtherContracts(e.target.checked)}
          label={
            <span className={"d-flex gap-2 align-items-center"}>
              Auch für weitere Verträge und Solidarbeitrag übernehmen
              <TapirHelpButton
                text={OTHER_CONTRACTS_HELP_TEXT}
                buttonSize={"sm"}
              />
            </span>
          }
        />
        {updateOtherContracts && (
          <ul className={"mt-2 mb-0"}>
            {affectedOtherSubscriptions.map((otherSubscription) => (
              <li
                key={`${otherSubscription.productId}-${otherSubscription.startDate}`}
              >
                {formatPublicSubscription(otherSubscription)} vom{" "}
                {formatDateNumeric(otherSubscription.startDate)} bis{" "}
                {formatDateNumeric(otherSubscription.endDate)}
              </li>
            ))}
            {solidarityContributions.map((contribution) => (
              <li key={contribution.id}>
                Solidarbeitrag{" "}
                {formatCurrency(Number.parseFloat(contribution.amount))} vom{" "}
                {formatDateNumeric(contribution.startDate)} bis{" "}
                {formatDateNumeric(contribution.endDate)}
              </li>
            ))}
          </ul>
        )}
      </>
    );
  }

  function getBodyContent() {
    if (mainDataLoading) {
      return <Spinner />;
    }

    if (subscription === undefined) {
      return <p>Fehler beim Laden der Vertragsdaten</p>;
    }

    const summaryLines = getSummaryLines(subscription);

    return (
      <ListGroup variant="flush">
        <ListGroup.Item>
          <ul className={"mb-0"}>
            <li>Produkt: {formatSubscription(subscription as Subscription)}</li>
            <li>Start: {formatDateNumeric(subscription.startDate)}</li>
            <li>Ende: {formatDateNumeric(subscription.endDate)}</li>
            {memberData && (
              <li>
                Mitglied: {memberData.firstName} {memberData.lastName}{" "}
                {memberData.memberNo && "#" + memberData.memberNo}
              </li>
            )}
          </ul>
        </ListGroup.Item>
        <ListGroup.Item>{getActionChoice(subscription)}</ListGroup.Item>
        {(choice?.action === ActionEnum.ChangeEnd ||
          choice?.action === ActionEnum.CancelRenewal) && (
          <ListGroup.Item>{getOtherContracts(subscription)}</ListGroup.Item>
        )}
        {summaryLines.length > 0 && (
          <ListGroup.Item>
            <h6>Was passiert</h6>
            <ul className={"mb-0"}>
              {summaryLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </ListGroup.Item>
        )}
        {error && (
          <ListGroup.Item>
            <Alert variant={"danger"} className={"mb-0"}>
              {error}
            </Alert>
          </ListGroup.Item>
        )}
      </ListGroup>
    );
  }

  return (
    <Modal onHide={onHide} show={show} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <span
          className={
            "d-flex flex-row justify-content-between align-items-center"
          }
          style={{ width: "100%" }}
        >
          <Modal.Title>Vertragslaufzeit anpassen / Sonderkündigung</Modal.Title>
          <TapirHelpButton text={HEADER_HELP_TEXT} />
        </span>
      </Modal.Header>

      <Modal.Body>{getBodyContent()}</Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          icon={"save"}
          text={"Daten ändern"}
          loading={mainDataLoading}
          disabled={!canSave()}
          onClick={onConfirmChange}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default SubscriptionChangeDatesModal;
