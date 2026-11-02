import React, { useState } from "react";
import { Table } from "react-bootstrap";
import { CoreApi, MailingListAdmin } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MailingListEditModal from "./MailingListEditModal.tsx";
import MailingListHeldMessagesModal from "./MailingListHeldMessagesModal.tsx";
import MailingListManageRecipientsModal from "./MailingListManageRecipientsModal.tsx";

interface MailingListsTableProps {
  mailingLists: MailingListAdmin[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  setMailingLists: (list: MailingListAdmin[]) => void;
  loadData: () => void;
}

const MailingListTable: React.FC<MailingListsTableProps> = ({
  mailingLists,
  setToastDatas,
  setMailingLists,
  loadData,
}) => {
  const api = useApi(CoreApi, getCsrfToken());
  const [listSelectedForDeletion, setListSelectedForDeletion] =
    useState<MailingListAdmin>();
  const [listSelectedForManagement, setListSelectedForManagement] =
    useState<MailingListAdmin>();
  const [listSelectedForEdit, setListSelectedForEdit] =
    useState<MailingListAdmin>();
  const [listSelectedForModeration, setListSelectedForModeration] =
    useState<MailingListAdmin>();
  const [deleting, setDeleting] = useState(false);

  function onDelete() {
    if (!listSelectedForDeletion) {
      alert("Keine Liste ausgewählt");
      return;
    }

    setDeleting(true);

    api
      .coreApiMailingListDeleteDestroy({
        listName: listSelectedForDeletion.name,
      })
      .then(() => {
        setMailingLists(
          mailingLists.filter(
            (list) => list.name !== listSelectedForDeletion.name,
          ),
        );
        setListSelectedForDeletion(undefined);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen der Mailing-List",
          setToastDatas,
        ),
      )
      .finally(() => setDeleting(false));
  }

  return (
    <>
      <Table striped hover responsive bordered>
        <thead>
          <tr>
            <th>Name</th>
            <th>Beschreibung</th>
            <th>Mitglieder können sich selber ein- und austragen</th>
            <th>Moderiert</th>
            <th>Empfänger</th>
            <th>Mails zur Freigabe</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {mailingLists.map((mailingList) => (
            <tr key={mailingList.name}>
              <td>{mailingList.name}</td>
              <td>
                <div className={"text-wrap"} style={{ maxWidth: "50dvw" }}>
                  {mailingList.description}
                </div>
              </td>
              <td>{mailingList.advertised ? "Ja" : "Nein"}</td>
              <td>{mailingList.moderated ? "Ja" : "Nein"}</td>
              <td>
                <TapirButton
                  icon={"manage_accounts"}
                  text={String(mailingList.nbRecipients)}
                  variant={"outline-primary"}
                  size={"sm"}
                  onClick={() => setListSelectedForManagement(mailingList)}
                />
              </td>
              <td>
                <TapirButton
                  icon={"approval"}
                  text={String(mailingList.nbHeldMessages)}
                  variant={"outline-primary"}
                  size={"sm"}
                  onClick={() => setListSelectedForModeration(mailingList)}
                  disabled={mailingList.nbHeldMessages === 0}
                />
              </td>

              <td>
                <span className={"d-flex flex-row gap-2"}>
                  <TapirButton
                    icon={"edit"}
                    variant={"outline-primary"}
                    size={"sm"}
                    onClick={() => setListSelectedForEdit(mailingList)}
                  />
                  <TapirButton
                    icon={"delete"}
                    variant={"outline-danger"}
                    size={"sm"}
                    onClick={() => setListSelectedForDeletion(mailingList)}
                  />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      {listSelectedForDeletion && (
        <ConfirmDeleteModal
          message={
            "Bist du sicher das du die Liste " +
            listSelectedForDeletion.name +
            " löschen willst?"
          }
          open={true}
          onConfirm={onDelete}
          onCancel={() => setListSelectedForDeletion(undefined)}
          loading={deleting}
        />
      )}
      {listSelectedForManagement && (
        <MailingListManageRecipientsModal
          show={true}
          onHide={() => setListSelectedForManagement(undefined)}
          loadData={loadData}
          setToastDatas={setToastDatas}
          listName={listSelectedForManagement.name}
        />
      )}
      {listSelectedForModeration && (
        <MailingListHeldMessagesModal
          show={true}
          onHide={() => setListSelectedForModeration(undefined)}
          loadData={loadData}
          setToastDatas={setToastDatas}
          listName={listSelectedForModeration.name}
        />
      )}
      {listSelectedForEdit && (
        <MailingListEditModal
          show={true}
          onHide={() => setListSelectedForEdit(undefined)}
          loadData={loadData}
          setToastDatas={setToastDatas}
          mailingList={listSelectedForEdit}
        />
      )}
    </>
  );
};

export default MailingListTable;
