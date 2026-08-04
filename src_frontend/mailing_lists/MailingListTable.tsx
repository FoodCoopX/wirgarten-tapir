import React, { useState } from "react";
import { Table } from "react-bootstrap";
import { CoreApi, MailingList } from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { getCsrfToken } from "../utils/getCsrfToken.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import MailingListManageRecipientsModal from "./MailingListManageRecipientsModal.tsx";

interface MailingListsTableProps {
  mailingLists: MailingList[];
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  setMailingLists: (list: MailingList[]) => void;
}

const MailingListTable: React.FC<MailingListsTableProps> = ({
  mailingLists,
  setToastDatas,
  setMailingLists,
}) => {
  const api = useApi(CoreApi, getCsrfToken());
  const [listSelectedForDeletion, setListSelectedForDeletion] =
    useState<MailingList>();
  const [listSelectedForManagement, setListSelectedForManagement] =
    useState<MailingList>();
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
            <th>Empfänger</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {mailingLists.map((mailingList) => (
            <tr key={mailingList.name}>
              <td>{mailingList.name}</td>
              <td>{mailingList.nbRecipients}</td>
              <td>
                <span className={"d-flex flex-row gap-2"}>
                  <TapirButton
                    icon={"contact_mail"}
                    variant={"outline-primary"}
                    size={"sm"}
                    onClick={() => setListSelectedForManagement(mailingList)}
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
          loadData={() => alert("Missing load data")}
          setToastDatas={setToastDatas}
          listName={listSelectedForManagement.name}
        />
      )}
    </>
  );
};

export default MailingListTable;
