import React, { useState } from "react";
import { Col, Row } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import { WaitingListApi, WaitingListEntryDetails } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { ToastData } from "../../types/ToastData.ts";
import { addToast } from "../../utils/addToast.ts";
import { formatDateText } from "../../utils/formatDateText.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface WaitingListTabLinkProps {
  entryDetails: WaitingListEntryDetails;
  reloadEntries: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  entryReloading: boolean;
}

const WaitingListTabLink: React.FC<WaitingListTabLinkProps> = ({
  entryDetails,
  reloadEntries,
  setToastDatas,
  entryReloading,
}) => {
  const api = useApi(WaitingListApi);
  const [loading, setLoading] = useState(false);

  function onSendLink() {
    setLoading(true);

    api
      .waitingListApiSendWaitingListLinkCreate({
        sendLinkSerializerRequest: { entryId: entryDetails.id },
      })
      .then(() => {
        reloadEntries();
        addToast(
          {
            title: "Mail versendet",
            variant: "success",
            id: uuidv4(),
          },
          setToastDatas,
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim versenden der Mail",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function onDisableLink() {
    setLoading(true);

    api
      .waitingListApiDisableWaitingListLinkCreate({
        disableLinkSerializerRequest: { entryId: entryDetails.id },
      })
      .then(() => {
        reloadEntries();
        addToast(
          {
            title: "Link ausgeschaltet",
            variant: "success",
            id: uuidv4(),
          },
          setToastDatas,
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim ausschalten der Link",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  function linkCanBeSent() {
    return (
      entryDetails.pickupLocationWishes !== undefined &&
      entryDetails.pickupLocationWishes.length <= 1
    );
  }

  return (
    <Row>
      <Col className={"mt-2"}>
        {entryDetails.linkSentDate ? (
          <p>
            Link geschickt am {formatDateText(entryDetails.linkSentDate, true)}
          </p>
        ) : (
          <p>Link nicht geschickt</p>
        )}
        {!linkCanBeSent() && (
          <p>
            <span className={"material-icons"}>warning</span> Bitte bearbeite
            bei den Verteilstation-Wünschen so, dass als einziger Wunsch die
            zukünftige Verteilstation verbleibt
          </p>
        )}
        <p>
          <TapirButton
            variant={"primary"}
            text={
              entryDetails.linkSentDate
                ? "Link erneut versenden"
                : "Link versenden"
            }
            icon={"send"}
            loading={loading || entryReloading}
            onClick={onSendLink}
            disabled={!linkCanBeSent()}
          />
        </p>
        {entryDetails.linkSentDate && (
          <p>
            <TapirButton
              variant={"danger"}
              text={"Link ausschalten"}
              icon={"link_off"}
              loading={loading || entryReloading}
              onClick={onDisableLink}
            />
          </p>
        )}
        {entryDetails.link && (
          <p>
            Link: <a href={entryDetails.link}>{entryDetails.link}</a>
          </p>
        )}
      </Col>
    </Row>
  );
};

export default WaitingListTabLink;
