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

  function buildHelpText() {
    return (
      <>
        <p>
          Über eine Mailing-Liste erreicht ihr eure Mitglieder per E-Mail, oder
          die Mitglieder tauschen sich darüber untereinander aus: Eine E-Mail an
          die Adresse der Liste wird an alle Empfänger der Liste weitergeleitet.
        </p>
        <p>
          Hier in Tapir legst du fest, wie eine Liste heißt, wie sie beschrieben
          ist, ob sich Mitglieder selbst ein- und austragen können und wer die
          Empfänger sind. Die Beschreibung sehen auch die Mitglieder. Schreib
          dort am besten hinein, wofür die Liste gedacht ist und wer schreiben
          darf.
        </p>
        <p>
          Alles Weitere stellst du nicht in Tapir ein, sondern FoodCoopX richtet
          es für euch ein: unter welcher Adresse eure Listen laufen (unter der
          Domain von FoodCoopX oder unter eurer eigenen), wer an eine Liste
          schreiben darf, ob E-Mails von Außenstehenden abgelehnt oder erst nach
          Freigabe weitergeleitet werden und ob es ein Archiv gibt.
        </p>
        <p>Was die Spalten bedeuten:</p>
        <ul>
          <li>
            <strong>Name</strong>: die E-Mail-Adresse der Liste.
          </li>
          <li>
            <strong>Mitglieder können sich selber ein- und austragen</strong>:
            Bei <em>Ja</em> sehen alle Mitglieder die Liste in ihrem
            Mitgliederbereich und können sich dort an- und abmelden. Bei{" "}
            <em>Nein</em> sehen nur eingeladene und bereits angemeldete
            Mitglieder die Liste.
          </li>
          <li>
            <strong>Empfänger</strong>: Anzahl der Empfänger, einschließlich der
            Einladungen, die noch nicht angenommen wurden.
          </li>
        </ul>
        <p>
          Über die Buttons rechts kannst du die Empfänger einer Liste verwalten,
          die Liste bearbeiten oder sie löschen.
        </p>
        <p>
          Empfänger, die du hinzufügst, werden zunächst nur eingeladen. Sie
          nehmen erst teil, wenn sie die Einladung angenommen haben. Mitglieder
          können das in ihrem Mitgliederbereich tun.
        </p>
      </>
    );
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
                  <TapirHelpButton text={buildHelpText()} width={"600px"} />
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
