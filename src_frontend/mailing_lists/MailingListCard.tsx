import React, { useEffect, useState } from "react";
import { Card, Col, Row, Spinner } from "react-bootstrap";
import { CoreApi, MailingList } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MailingListCreateModal from "./MailingListCreateModal.tsx";
import MailingListTable from "./MailingListTable.tsx";

const MailingListCard: React.FC = () => {
  const api = useApi(CoreApi, getCsrfToken());
  const [mailingListsLoading, setMailingListsLoading] = useState(true);
  const [mailingLists, setMailingLists] = useState<MailingList[]>([]);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setMailingListsLoading(true);

    api
      .coreApiMailingListListList()
      .then(setMailingLists)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mailing-Listen",
          setToastDatas,
        ),
      )
      .finally(() => setMailingListsLoading(false));
  }

  return (
    <>
      <Row className={"mt-2"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex flex-row justify-content-between align-items-center"
                }
              >
                <Card.Title className={"mb-0"}>Mailing-Listen</Card.Title>
                <span className={"d-flex gap-2"}>
                  <TapirHelpButton
                    text={"HelpText Mailing-List Config-Title"}
                  />
                  <TapirButton
                    icon={"add"}
                    text={"Mailing-List erzeugen"}
                    variant={"outline-primary"}
                    onClick={() => setShowCreateModal(true)}
                  />
                </span>
              </div>
            </Card.Header>
            <Card.Body>
              {mailingListsLoading ? (
                <Spinner />
              ) : (
                <MailingListTable
                  mailingLists={mailingLists}
                  setMailingLists={setMailingLists}
                  setToastDatas={setToastDatas}
                  loadData={loadData}
                />
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <MailingListCreateModal
        show={showCreateModal}
        onHide={() => setShowCreateModal(false)}
        loadData={loadData}
        setToastDatas={setToastDatas}
      />
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MailingListCard;
