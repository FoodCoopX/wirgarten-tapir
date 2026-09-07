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
          "Fehler bei der Anmeldung an eine Liste",
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
          "Fehler bei der Abmeldung an eine Liste",
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
          "Fehler bei der Bestätigung der Einladung an eine Liste",
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
          "Fehler beim Ablehnen der Einladung an eine Liste",
          setToastDatas,
        ),
      )
      .finally(() => setListLoading(undefined));
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
        Du bist zu diese Liste eingeladen. Du kannst die Einladung annehmen oder
        ablehnen.
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
          text={"Sich abmelden"}
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
            text={"Anmeldung bestätigen"}
            onClick={() => onConfirm(list)}
          />
          <TapirButton
            size={"sm"}
            variant={"primary"}
            icon={"unsubscribe"}
            text={"Anmeldung ablehnen"}
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
        text={"Sich anmelden"}
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
            <TapirHelpButton text={"HelpText Mailing-List Mitgliederbereich"} />
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
