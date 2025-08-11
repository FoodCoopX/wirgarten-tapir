import React, { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi.ts";
import { WaitingListApi, WaitingListEntryDetails } from "../api-client";
import { ToastData } from "../types/ToastData.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { handleRequestError } from "../utils/handleRequestError.ts";
import BestellWizard from "../bestell_wizard/BestellWizard.tsx";
import { Card, Col, ListGroup, Row, Spinner } from "react-bootstrap";

interface WaitingListConfirmBaseProps {
  csrfToken: string;
  waitingListEntryId: string;
  waitingListLinkKey: string;
  adminEmail: string;
}

const WaitingListConfirmBase: React.FC<WaitingListConfirmBaseProps> = ({
  csrfToken,
  waitingListEntryId,
  waitingListLinkKey,
  adminEmail,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [loading, setLoading] = useState(true);
  const [waitingListEntryDetails, setWaitingListEntryDetails] =
    useState<WaitingListEntryDetails>();

  useEffect(() => {
    api
      .waitingListApiPublicGetWaitingListEntryDetailsRetrieve({
        entryId: waitingListEntryId,
        linkKey: waitingListLinkKey,
      })
      .then(setWaitingListEntryDetails)
      .catch(async (error) => {
        if (error?.response?.status === 404) return;
        await handleRequestError(
          error,
          "Fehler beim Laden der Warteliste-Eintrag!",
          setToastDatas,
        );
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      {waitingListEntryDetails ? (
        <BestellWizard
          csrfToken={csrfToken}
          waitingListEntryDetails={waitingListEntryDetails}
        />
      ) : (
        <>
          <Row className={"justify-content-center p-4"}>
            <Col style={{ maxWidth: "1200px" }}>
              <Card style={{ height: "95vh" }}>
                <Card.Header>{loading ? "Laden..." : "Fehler"}</Card.Header>
                <ListGroup
                  variant={"flush"}
                  style={{
                    overflowX: "hidden",
                    height: "100%",
                  }}
                >
                  <ListGroup.Item
                    style={{
                      height: "100%",
                      overflowY: "scroll",
                      overflowX: "hidden",
                    }}
                  >
                    {loading ? (
                      <Spinner />
                    ) : (
                      <p>
                        Der Link ist bereits abgelaufen. Bitte wende dich an{" "}
                        <a href={"mailto:" + adminEmail}>{adminEmail}</a>
                      </p>
                    )}
                  </ListGroup.Item>
                </ListGroup>
              </Card>
            </Col>
          </Row>
        </>
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default WaitingListConfirmBase;
