import { ArrowPathIcon, XMarkIcon } from "@heroicons/react/24/outline";
import React, { useEffect, useState } from "react";
import { Badge, Modal, Table } from "react-bootstrap";
import {
  DispatchStatusEnum,
  EmailConfigurationDispatch,
  EmailDispatch,
  EmailDispatchWithRetries,
  TapirmailApi,
} from "tapir-api-client";
import { useAlert } from "../contexts/alerts";
import { useApi } from "../hooks/useApi";
import { EMAIL_DISPATCH_STATUS_PROPS } from "../utils/emailDispatchStatusProps";
import { formatDate } from "../utils/formatDate";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination";
import EmailConfigurationDispatchStats from "./dashboard/EmailConfigurationDispatchStats";
import DispatchErrorMessage from "./DispatchErrorMessage";
import TapirButton from "./TapirButton";
import TapirDropdown, { Choice } from "./tapirDropdown";
import TapirHelpButton from "./TapirHelpButton";
import TapirPagination from "./TapirPagination";
import TapirTooltip from "./TapirTooltip";

interface DispatchDetailsModalProps {
  configDispatch: EmailConfigurationDispatch;
  open: boolean;
  onClose: () => void;
}

const DispatchDetailsModal: React.FC<DispatchDetailsModalProps> = ({
  configDispatch,
  open,
  onClose,
}) => {
  const [dispatches, setDispatches] = useState<EmailDispatchWithRetries[]>([]);
  const emailDispatchApi = useApi(TapirmailApi);
  const emailConfigDispatchApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [currentPage, setCurrentPage] = useState(0);
  const [dispatchCount, setDispatchCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState<Choice>();

  const filterChoices: Choice[] = [];
  let key: keyof typeof EMAIL_DISPATCH_STATUS_PROPS;
  for (key in EMAIL_DISPATCH_STATUS_PROPS) {
    filterChoices.push({
      id: key,
      name: EMAIL_DISPATCH_STATUS_PROPS[key].text,
    });
  }

  useEffect(() => {
    loadData();

    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [configDispatch, currentPage, statusFilter]);

  function loadData() {
    emailDispatchApi
      .tapirmailApiEmailDispatchList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
        configDispatchId: configDispatch.id,
        dispatchStatus: statusFilter?.id.toString(),
      })
      .then((paginatedData) => {
        setDispatches(paginatedData.results ?? []);
        setDispatchCount(paginatedData.count ?? 0);
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Laden der Dispatches", "danger");
      });
  }

  function renderDetails(dispatch: EmailDispatch) {
    switch (dispatch.dispatchStatus) {
      case "bounced":
        return (
          <span>
            Bounce-Typ "{dispatch.bounceType}" mit Nachricht :{" "}
            {dispatch.bounceMessage}
          </span>
        );
      case "error":
        return <DispatchErrorMessage errorMessage={dispatch.errorMessage} />;
      case "opened":
        return <span>Geöffnet am {formatDate(dispatch.openedTime)}</span>;
      case "unknown":
        return <span></span>;
      case "sending":
        return renderPendingAutomaticRetry(dispatch);
    }
  }

  function renderPendingAutomaticRetry(dispatch: EmailDispatch) {
    if (!dispatch.isAutomaticRetry || !dispatch.notBefore) {
      return <span></span>;
    }
    const reason =
      "Der vorherige Versuch ist an einem vorübergehenden Fehler gescheitert (z.B. Mailserver nicht erreichbar). ";
    if (dispatch.notBefore > new Date()) {
      return (
        <span>
          {reason}Automatischer erneuter Versuch ab{" "}
          {formatDate(dispatch.notBefore)}.
        </span>
      );
    }
    return <span>{reason}Automatischer erneuter Versuch in Kürze.</span>;
  }

  function retryConfigDispatch() {
    emailConfigDispatchApi
      .tapirmailApiEmailConfigurationDispatchRetryallCreate({
        id: configDispatch.id,
        emailConfigurationDispatchRequest: configDispatch,
      })
      .then(() => {
        loadData();
        showAlert("Email wird erneut versendet.", "success");
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim erneutem Versand!", "danger");
      });
  }

  function retrySingleDispatch(dispatch: EmailDispatch) {
    emailDispatchApi
      .tapirmailApiEmailDispatchRetryCreate({
        id: dispatch.id!,
        emailDispatchRequest: dispatch,
      })
      .then(() => {
        loadData();
        showAlert("Email wird erneut versendet.", "success");
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim erneutem Versand!", "danger");
      });
  }

  const tableStripeColor = "var(--bs-table-striped-bg)";

  return (
    <Modal show={open} onHide={onClose} size="xl" centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>
          Versand Details: "
          {configDispatch.emailConfigurationVersion.emailConfiguration.name}"
          gesendet am {formatDate(configDispatch.scheduledTime)}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="d-flex justify-content-between align-items-center">
          <span className={"d-flex align-items-center gap-2"}>
            <TapirDropdown
              choices={filterChoices}
              onChoiceSelected={(choice) => {
                setStatusFilter(choice ?? undefined);
              }}
              selectedChoice={statusFilter}
              noSelectionText="Status filtern"
            />
            {statusFilter && (
              <TapirTooltip id="reset-filters" text="Filter löschen">
                <TapirButton
                  icon={XMarkIcon}
                  onClick={() => setStatusFilter(undefined)}
                />
              </TapirTooltip>
            )}
            <TapirHelpButton
              text={
                <ul>
                  {Object.entries(EMAIL_DISPATCH_STATUS_PROPS).map(
                    ([key, value]) => (
                      <li key={key}>
                        <Badge bg={value.color}>{value.text}</Badge>:{" "}
                        {value.extraText}
                      </li>
                    ),
                  )}
                </ul>
              }
              width={"80vw"}
            />
          </span>
          <TapirButton
            variant={
              configDispatch.errorCount === 0
                ? "outline-secondary"
                : "outline-primary"
            }
            icon={ArrowPathIcon}
            text={"Alle Fehler erneut versuchen"}
            disabled={configDispatch.errorCount === 0}
            onClick={retryConfigDispatch}
          />
          <EmailConfigurationDispatchStats
            emailConfigurationDispatch={configDispatch}
          />
        </div>
        <Table style={{ marginTop: "1em" }} hover responsive>
          <thead>
            <tr>
              <th>Adresse</th>
              <th style={{ textAlign: "center" }}>Zeitpunkt</th>
              <th style={{ textAlign: "center" }}>Status</th>
              <th>Details</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {dispatches.map(
              (dispatch: EmailDispatchWithRetries, index: number) => (
                <>
                  <tr
                    style={
                      index % 2
                        ? undefined
                        : { backgroundColor: tableStripeColor }
                    }
                  >
                    <td style={{ background: "inherit", whiteSpace: "nowrap" }}>
                      {dispatch.recipient}
                    </td>
                    <td
                      style={{
                        background: "inherit",
                        textAlign: "center",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDate(dispatch.sentTime ?? dispatch.createdAt)}
                    </td>
                    <td
                      style={{
                        background: "inherit",
                        textAlign: "center",
                      }}
                    >
                      <Badge
                        bg={
                          EMAIL_DISPATCH_STATUS_PROPS[dispatch.dispatchStatus]
                            .color
                        }
                      >
                        {
                          EMAIL_DISPATCH_STATUS_PROPS[dispatch.dispatchStatus]
                            .text
                        }
                      </Badge>
                    </td>
                    <td style={{ background: "inherit" }}>
                      {renderDetails(dispatch)}
                    </td>
                    <td style={{ background: "inherit" }}>
                      {dispatch.dispatchStatus !== DispatchStatusEnum.Sending &&
                        (dispatch.nextRetry ? (
                          <span>Dies ist schon erneut versendet worden.</span>
                        ) : (
                          <TapirTooltip
                            id={"resend-" + dispatch.id}
                            text="Erneut senden"
                          >
                            <TapirButton
                              variant={
                                dispatch.dispatchStatus ===
                                  DispatchStatusEnum.Error ||
                                dispatch.dispatchStatus ===
                                  DispatchStatusEnum.Bounced
                                  ? "outline-primary"
                                  : "outline-secondary"
                              }
                              size="sm"
                              icon={ArrowPathIcon}
                              onClick={() => retrySingleDispatch(dispatch)}
                            />
                          </TapirTooltip>
                        ))}
                    </td>
                  </tr>
                  {dispatch.previousRetries.map((retry: EmailDispatch) => (
                    <tr
                      key={retry.id}
                      style={
                        index % 2
                          ? undefined
                          : { backgroundColor: tableStripeColor }
                      }
                    >
                      <td style={{ background: "inherit", paddingLeft: "3em" }}>
                        →
                      </td>
                      <td
                        style={{
                          background: "inherit",
                          textAlign: "center",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {formatDate(retry.sentTime ?? retry.createdAt)}
                      </td>
                      <td
                        style={{ background: "inherit", textAlign: "center" }}
                      >
                        <Badge
                          bg={
                            EMAIL_DISPATCH_STATUS_PROPS[retry.dispatchStatus]
                              .color
                          }
                        >
                          {
                            EMAIL_DISPATCH_STATUS_PROPS[retry.dispatchStatus]
                              .text
                          }
                        </Badge>
                      </td>
                      <td style={{ background: "inherit" }} colSpan={2}>
                        {renderDetails(retry)}
                      </td>
                    </tr>
                  ))}
                </>
              ),
            )}
          </tbody>
        </Table>
      </Modal.Body>
      {dispatchCount > DEFAULT_PAGE_SIZE && (
        <Modal.Footer className="d-flex justify-content-center align-items-center">
          <TapirPagination
            pageSize={DEFAULT_PAGE_SIZE}
            currentPage={currentPage}
            goToPage={setCurrentPage}
            itemCount={dispatchCount}
          />
        </Modal.Footer>
      )}
    </Modal>
  );
};

export default DispatchDetailsModal;
