import React, { useEffect, useState } from "react";
import { Modal, Spinner } from "react-bootstrap";
import { CoreApi, SubscriptionManagementData } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import MailingListsCard from "../member_profile/mailing_lists/MailingListsCard.tsx";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import SubscriptionManagementExternalCard from "./SubscriptionManagementExternalCard.tsx";
import SubscriptionManagementExtraCard from "./SubscriptionManagementExtraCard.tsx";

type Removal = "extra" | "external";

interface SubscriptionManagementProps {
  token: string;
}

const SubscriptionManagement: React.FC<SubscriptionManagementProps> = ({
  token,
}) => {
  const api = useApi(CoreApi);
  const [data, setData] = useState<SubscriptionManagementData>();
  const [saving, setSaving] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState<Removal>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  function loadData() {
    api
      .coreApiSubscriptionManagementDataRetrieve({ token: token })
      .then(setData)
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Abos", setToastDatas),
      );
  }

  function runAndReload(promise: Promise<unknown>, errorMessage: string) {
    setSaving(true);
    promise
      .then(loadData)
      .catch((error) => handleRequestError(error, errorMessage, setToastDatas))
      .finally(() => {
        setSaving(false);
        setPendingRemoval(undefined);
      });
  }

  function onSaveExtraCategories(categoriesRegisteredTo: {
    [key: string]: boolean;
  }) {
    runAndReload(
      api.coreApiSubscriptionManagementExtraCategoriesCreate({
        subscriptionManagementCategoriesRequestRequest: {
          token: token,
          categoriesRegisteredTo: categoriesRegisteredTo,
        },
      }),
      "Fehler beim Speichern der Mail-Abos",
    );
  }

  function onSaveExternal(
    firstName: string,
    categoriesRegisteredTo: { [key: string]: boolean },
  ) {
    runAndReload(
      api.coreApiSubscriptionManagementExternalCreate({
        subscriptionManagementExternalRequestRequest: {
          token: token,
          firstName: firstName,
          categoriesRegisteredTo: categoriesRegisteredTo,
        },
      }),
      "Fehler beim Speichern der Newsletter-Abos",
    );
  }

  function onConfirmRemoval() {
    if (pendingRemoval === "extra") {
      runAndReload(
        api.coreApiSubscriptionManagementExtraDestroy({ token: token }),
        "Fehler beim Entfernen der zusätzlichen Adresse",
      );
    } else {
      runAndReload(
        api.coreApiSubscriptionManagementExternalDestroy({ token: token }),
        "Fehler beim Abmelden",
      );
    }
  }

  function buildMailingListRequest(listName: string) {
    return {
      subscriptionManagementMailingListRequestRequest: {
        token: token,
        listName: listName,
      },
    };
  }

  function buildMailingListsCard() {
    if (!data?.mailingLists || data.mailingLists.availableLists.length === 0) {
      return null;
    }

    return (
      <MailingListsCard
        addressLabel={"dieser Adresse"}
        loadListData={() =>
          api
            .coreApiSubscriptionManagementDataRetrieve({ token: token })
            .then((response) => response.mailingLists!)
        }
        subscribe={(listName) =>
          api.coreApiSubscriptionManagementMailingListSubscribeCreate(
            buildMailingListRequest(listName),
          )
        }
        unsubscribe={(listName) =>
          api.coreApiSubscriptionManagementMailingListUnsubscribeCreate(
            buildMailingListRequest(listName),
          )
        }
        acceptInvitation={(listName) =>
          api.coreApiSubscriptionManagementMailingListAcceptInvitationCreate(
            buildMailingListRequest(listName),
          )
        }
        rejectInvitation={(listName) =>
          api.coreApiSubscriptionManagementMailingListRejectInvitationCreate(
            buildMailingListRequest(listName),
          )
        }
        setToastDatas={setToastDatas}
      />
    );
  }

  function buildRemovalText() {
    if (pendingRemoval === "extra") {
      return `Diese Adresse bekommt dann keine Mails mehr über ${data?.extra?.memberFirstName} und wird von allen Mailing-Listen abgemeldet.`;
    }
    return "Diese Adresse bekommt dann keinen Newsletter mehr und wird von allen Mailing-Listen abgemeldet.";
  }

  if (data === undefined) {
    return (
      <>
        <Spinner />
        <TapirToastContainer
          toastDatas={toastDatas}
          setToastDatas={setToastDatas}
        />
      </>
    );
  }

  const hasNothingToManage =
    !data.extra &&
    !data.external &&
    (!data.mailingLists || data.mailingLists.availableLists.length === 0);

  return (
    <>
      <div className={"d-flex flex-column gap-3"}>
        {hasNothingToManage && (
          <p>Für diese Adresse gibt es nichts zu verwalten.</p>
        )}
        {data.extra && (
          <SubscriptionManagementExtraCard
            extra={data.extra}
            saving={saving}
            onSave={onSaveExtraCategories}
            onRemove={() => setPendingRemoval("extra")}
          />
        )}
        {data.external && (
          <SubscriptionManagementExternalCard
            external={data.external}
            saving={saving}
            onSave={onSaveExternal}
            onRemove={() => setPendingRemoval("external")}
          />
        )}
        {buildMailingListsCard()}
      </div>
      <Modal
        show={pendingRemoval !== undefined}
        onHide={() => setPendingRemoval(undefined)}
        centered
      >
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Wirklich entfernen?</h5>
        </Modal.Header>
        <Modal.Body>{buildRemovalText()}</Modal.Body>
        <Modal.Footer>
          <TapirButton
            variant={"outline-secondary"}
            text={"Abbrechen"}
            onClick={() => setPendingRemoval(undefined)}
          />
          <TapirButton
            variant={"danger"}
            text={"Entfernen"}
            onClick={onConfirmRemoval}
            loading={saving}
          />
        </Modal.Footer>
      </Modal>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default SubscriptionManagement;
