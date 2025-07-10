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
}

const WaitingListConfirmBase: React.FC<WaitingListConfirmBaseProps> = ({
  csrfToken,
  waitingListEntryId,
  waitingListLinkKey,
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
      .catch((error) =>
        handleRequestError(error, "Fehler vom Server!", addToast),
      )
      .finally(() => setLoading(false));
  }, []);

  function addToast(toastData: ToastData) {
    setToastDatas((datas) => {
      datas.push(toastData);
      return [...datas];
    });
  }

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
                <Card.Header>Laden...</Card.Header>
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
                    {loading ? <Spinner /> : "Fehler"}
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
