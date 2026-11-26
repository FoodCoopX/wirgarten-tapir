import React, { useEffect, useState } from "react";
import { Card, Table } from "react-bootstrap";
import {
  EmailConfigurationDispatch,
  EmailConfigurationVersion,
  SegmentOption,
  TapirmailApi,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import { buildSegmentDataFromVersion } from "../../utils/buildSegmentDataFromVersion";
import { formatDate } from "../../utils/formatDate";
import { DEFAULT_PAGE_SIZE } from "../../utils/pagination";
import DispatchDetailsModal from "../DispatchDetailsModal";
import Loading from "../loading";
import SegmentsDisplay from "../segmentsDisplay";
import TapirPagination from "../TapirPagination";
import TapirTooltip from "../TapirTooltip";
import { EmailConfigurationDispatchStats } from "./EmailConfigurationDispatchStats";
import SelectVersionModal from "./SelectVersionModal";

interface EmailConfigurationVersionStatusTableProps {
  cardTitle: string;
  content: "last-sent" | "next-sends";
}

const EmailConfigurationDispatchTable: React.FC<
  EmailConfigurationVersionStatusTableProps
> = ({ cardTitle, content }) => {
  const api = useApi(TapirmailApi);
  const segmentApi = useApi(TapirmailApi);
  const showAlert = useAlert();

  const [emailConfigurationDispatches, setEmailConfigurationDispatches] =
    useState<EmailConfigurationDispatch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [dispatchCount, setDispatchCount] = useState(0);
  const [
    selectedEmailConfigurationVersion,
    setSelectedEmailConfigurationVersion,
  ] = useState<EmailConfigurationVersion>();
  const [
    emailConfigurationDispatchForStats,
    setEmailConfigurationDispatchForStats,
  ] = useState<EmailConfigurationDispatch>();
  const [availableSegments, setAvailableSegments] = useState<SegmentOption[]>(
    [],
  );

  useEffect(() => {
    segmentApi
      .tapirmailApiSegmentAvailableSegmentsRetrieve()
      .then((response) => {
        setAvailableSegments(response.segments);
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim Laden der Segment-Daten", "danger");
      });
  }, []);

  const fetchEmailConfigurationDispatch = () => {
    let call;
    switch (content) {
      case "last-sent":
        call = api.tapirmailApiEmailConfigurationDispatchLastSentList.bind(api);
        break;
      case "next-sends":
        call =
          api.tapirmailApiEmailConfigurationDispatchNextSendsList.bind(api);
        break;
    }

    call({
      limit: DEFAULT_PAGE_SIZE,
      offset: currentPage * DEFAULT_PAGE_SIZE,
    })
      .then((paginatedData) => {
        setEmailConfigurationDispatches(paginatedData.results ?? []);
        setDispatchCount(paginatedData.count ?? 0);
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim Laden der Emails", "danger");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchEmailConfigurationDispatch();

    const interval = setInterval(() => {
      fetchEmailConfigurationDispatch();
    }, 30000);

    return () => clearInterval(interval);
  }, [currentPage]);

  function hasRecipientOverride(dispatch: EmailConfigurationDispatch): boolean {
    if (!dispatch.overrideRecipients) {
      return false;
    }

    if (Array.isArray(dispatch.overrideRecipients)) {
      return dispatch.overrideRecipients.length > 0;
    }

    return true;
  }

  return (
    <>
      <Card>
        <Card.Header
          as="h5"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{cardTitle}</span>
        </Card.Header>
        <Card.Body style={{ padding: 0, border: "none" }}>
          {loading ? (
            <Loading />
          ) : (
            <Table striped hover style={{ margin: "0" }} responsive>
              <thead>
                <tr>
                  <th>Name</th>
                  {content === "last-sent" && (
                    <>
                      <th>Gesendet am</th>
                      <th>Empfänger</th>
                      <th>Öffnungsrate</th>
                    </>
                  )}
                  {content === "next-sends" && (
                    <>
                      <th>Versandzeitpunkt</th>
                      <th>Empfänger</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {emailConfigurationDispatches.map(
                  (emailConfigurationDispatch) => (
                    <tr
                      style={{ cursor: "pointer" }}
                      key={content + "-" + emailConfigurationDispatch.id}
                      onClick={() =>
                        setSelectedEmailConfigurationVersion(
                          emailConfigurationDispatch.emailConfigurationVersion,
                        )
                      }
                    >
                      <td>
                        {
                          emailConfigurationDispatch.emailConfigurationVersion
                            .emailConfiguration.name
                        }
                      </td>
                      <td>
                        {formatDate(emailConfigurationDispatch.scheduledTime)}
                      </td>
                      <td>
                        {hasRecipientOverride(emailConfigurationDispatch) ? (
                          <span className={"text-break"}>
                            {
                              emailConfigurationDispatch.overrideRecipientsDisplay
                            }
                          </span>
                        ) : (
                          <SegmentsDisplay
                            segmentData={buildSegmentDataFromVersion(
                              emailConfigurationDispatch.emailConfigurationVersion,
                            )}
                            availableSegments={availableSegments}
                          />
                        )}
                      </td>
                      {content === "last-sent" && (
                        <td
                          style={{ padding: "0.1em", margin: "0" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setEmailConfigurationDispatchForStats(
                              emailConfigurationDispatch,
                            );
                          }}
                        >
                          <TapirTooltip
                            text="Details anzeigen"
                            id={content + "-" + emailConfigurationDispatch.id}
                          >
                            <div style={{ width: "100%", height: "100%" }}>
                              <EmailConfigurationDispatchStats
                                emailConfigurationDispatch={
                                  emailConfigurationDispatch
                                }
                              />
                            </div>
                          </TapirTooltip>
                        </td>
                      )}
                    </tr>
                  ),
                )}
              </tbody>
            </Table>
          )}
        </Card.Body>
        {dispatchCount > DEFAULT_PAGE_SIZE && (
          <Card.Footer className="d-flex justify-content-center align-items-center">
            <TapirPagination
              pageSize={DEFAULT_PAGE_SIZE}
              itemCount={dispatchCount}
              currentPage={currentPage}
              goToPage={setCurrentPage}
            />
          </Card.Footer>
        )}
      </Card>
      <SelectVersionModal
        open={!!selectedEmailConfigurationVersion}
        emailConfiguration={
          selectedEmailConfigurationVersion?.emailConfiguration!
        }
        onClose={() => setSelectedEmailConfigurationVersion(undefined)}
        onDataChanged={fetchEmailConfigurationDispatch}
        selectedVersionOnOpen={selectedEmailConfigurationVersion?.id}
      />
      {emailConfigurationDispatchForStats && (
        <DispatchDetailsModal
          configDispatch={emailConfigurationDispatchForStats}
          open={!!emailConfigurationDispatchForStats}
          onClose={() => setEmailConfigurationDispatchForStats(undefined)}
        />
      )}
    </>
  );
};

export default EmailConfigurationDispatchTable;
