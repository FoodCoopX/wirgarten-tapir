import "dayjs/locale/de";
import React, { useEffect, useState } from "react";
import { Card, Spinner, Table } from "react-bootstrap";
import { CoreApi, MailingList } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";
import TapirToastContainer from "../../components/TapirToastContainer.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface MemberMailCategoryModalProps {
  memberId: string;
  csrfToken: string;
}

const MemberMailingListsCard: React.FC<MemberMailCategoryModalProps> = ({
  memberId,
  csrfToken,
}) => {
  const api = useApi(CoreApi, csrfToken);
  const [allMailingLists, setAllMailingLists] = useState<MailingList[]>([]);
  const [subscribedLists, setSubscribedLists] = useState<string[]>([]);
  const [waitingForConfirmationLists, setWaitingForConfirmationLists] =
    useState<string[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [listLoading, setListLoading] = useState<MailingList>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    setDataLoading(true);
    api
      .coreApiMemberMailingListDataRetrieve({ memberId: memberId })
      .then((data) => {
        setAllMailingLists(data.availableLists);
        setSubscribedLists(data.subscribedLists);
        setWaitingForConfirmationLists(data.waitingForConfirmationLists);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Mailing-Listen",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  function onSubscribe(list: MailingList) {
    setListLoading(list);

    api
      .coreApiMemberSelfSubscribeCreate({
        mailingListSubscribeInternalRecipientRequestRequest: {
          listName: list.name,
          memberId: memberId,
        },
      })
      .then(() => loadData())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler bei der Anmeldung bei einer Liste",
          setToastDatas,
        ),
      )
      .finally(() => setListLoading(undefined));
  }

  function onUnsubscribe(list: MailingList) {
    setListLoading(list);

    api
      .coreApiMemberSelfUnsubscribeCreate({
        mailingListSubscribeInternalRecipientRequestRequest: {
          listName: list.name,
          memberId: memberId,
        },
      })
      .then(() => loadData())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler bei der Abmeldung von einer Liste",
          setToastDatas,
        ),
      )
      .finally(() => setListLoading(undefined));
  }

  function onConfirm(list: MailingList) {
    setListLoading(list);

    api
      .coreApiMemberSelfConfirmCreate({
        mailingListSubscribeInternalRecipientRequestRequest: {
          listName: list.name,
          memberId: memberId,
        },
      })
      .then(() => loadData())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler bei der Bestätigung der Einladung zu einer Liste",
          setToastDatas,
        ),
      )
      .finally(() => setListLoading(undefined));
  }

  function onReject(list: MailingList) {
    setListLoading(list);

    api
      .coreApiMemberSelfRejectCreate({
        mailingListSubscribeInternalRecipientRequestRequest: {
          listName: list.name,
          memberId: memberId,
        },
      })
      .then(() => loadData())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Ablehnen der Einladung zu einer Liste",
          setToastDatas,
        ),
      )
      .finally(() => setListLoading(undefined));
  }

  function buildHelpText() {
    return (
      <>
        <p>
          Über eine Mailing-Liste kannst du dich per E-Mail mit anderen
          Mitgliedern austauschen: Eine E-Mail an die Adresse der Liste wird an
          alle weitergeleitet, die an der Liste teilnehmen.
        </p>
        <p>Was die Spalten bedeuten:</p>
        <ul>
          <li>
            <strong>Liste</strong>: die E-Mail-Adresse der Liste. An diese
            Adresse schreibst du, um alle Teilnehmenden zu erreichen.
          </li>
          <li>
            <strong>Beschreibung</strong>: Mit einem Klick auf das Fragezeichen
            siehst du, wofür die Liste gedacht ist.
          </li>
          <li>
            <strong>Teilnahme</strong>: <em>Ja</em> – du nimmst teil und
            bekommst die E-Mails der Liste. <em>Nein</em> – du nimmst nicht
            teil. <em>Eingeladen</em> – du wurdest eingeladen und nimmst erst
            teil, wenn du die Einladung annimmst.
          </li>
        </ul>
        <p>So funktioniert es:</p>
        <ul>
          <li>
            Mit „Anmelden“ nimmst du sofort an der Liste teil, und zwar mit der
            E-Mail-Adresse aus deinem Profil. Du musst nichts weiter bestätigen
            und bekommst auch keine Bestätigungs-E-Mail. Dass die Anmeldung
            geklappt hat, erkennst du daran, dass bei Teilnahme „Ja“ steht.
          </li>
          <li>
            Um an alle zu schreiben, schickst du aus deinem E-Mail-Programm eine
            E-Mail an die Adresse der Liste. Nutze dafür die E-Mail-Adresse aus
            deinem Profil als Absender.
          </li>
          <li>
            Mit „Abmelden“ beendest du deine Teilnahme. Du bekommst dann keine
            E-Mails der Liste mehr.
          </li>
        </ul>
      </>
    );
  }

  function buildParticipation(list: MailingList) {
    if (subscribedLists.includes(list.name)) {
      return "Ja";
    }

    if (waitingForConfirmationLists.includes(list.name)) {
      return (
        <span className={"d-flex gap-2 align-items-start"}>
          <span>Eingeladen</span>
          <TapirHelpButton
            buttonSize={"sm"}
            text={buildInvitationHelpText(list)}
          />
        </span>
      );
    }

    return "Nein";
  }

  function buildInvitationHelpText(list: MailingList) {
    let text = (
      <p>
        Du bist zu dieser Liste eingeladen. Du kannst die Einladung annehmen
        oder ablehnen.
      </p>
    );

    if (!list.advertised) {
      text = (
        <>
          {text}
          <p>
            Wenn du die Einladung ablehnst, kannst du dich nicht mehr für die
            Liste anmelden. Es müsste ein Administrator dich wieder einladen.
          </p>
        </>
      );
    }

    return text;
  }

  function buildButtons(list: MailingList) {
    if (subscribedLists.includes(list.name)) {
      return (
        <TapirButton
          size={"sm"}
          variant={"primary"}
          icon={"unsubscribe"}
          text={"Abmelden"}
          onClick={() => onUnsubscribe(list)}
        />
      );
    }

    if (waitingForConfirmationLists.includes(list.name)) {
      return (
        <span className={"d-flex gap-2"}>
          <TapirButton
            size={"sm"}
            variant={"primary"}
            icon={"mark_email_read"}
            text={"Einladung annehmen"}
            onClick={() => onConfirm(list)}
          />
          <TapirButton
            size={"sm"}
            variant={"primary"}
            icon={"unsubscribe"}
            text={"Einladung ablehnen"}
            onClick={() => onReject(list)}
          />
        </span>
      );
    }

    return (
      <TapirButton
        size={"sm"}
        variant={"primary"}
        icon={"mail"}
        text={"Anmelden"}
        onClick={() => onSubscribe(list)}
        loading={listLoading === list}
      />
    );
  }

  return (
    <>
      <Card>
        <Card.Header>
          <span
            className={
              "d-flex flex-row justify-content-between align-items-center"
            }
          >
            <h5 className={"mb-0"}>Mailing-Listen</h5>
            <TapirHelpButton text={buildHelpText()} width={"600px"} />
          </span>
        </Card.Header>
        <Card.Body>
          {dataLoading ? (
            <Spinner />
          ) : (
            <Table responsive bordered striped>
              <thead>
                <tr>
                  <th>Liste</th>
                  <th>Beschreibung</th>
                  <th>Teilnahme</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {allMailingLists.map((list) => (
                  <tr key={list.name}>
                    <td>{list.name}</td>
                    <td>
                      <TapirHelpButton
                        text={list.description}
                        buttonSize={"sm"}
                        title={"Beschreibung"}
                      />
                    </td>
                    <td>{buildParticipation(list)}</td>
                    <td>{buildButtons(list)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default MemberMailingListsCard;
