import React, { useState } from "react";
import { Col, Row } from "react-bootstrap";
import { WaitingListApi, WaitingListEntryDetails } from "../../api-client";
import { formatDateText } from "../../utils/formatDateText.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";
import { v4 as uuidv4 } from "uuid";
import { addToast } from "../../utils/addToast.ts";

interface WaitingListTabLinkProps {
  entryDetails: WaitingListEntryDetails;
  csrfToken: string;
  reloadEntries: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const WaitingListTabLink: React.FC<WaitingListTabLinkProps> = ({
  entryDetails,
  csrfToken,
  reloadEntries,
  setToastDatas,
}) => {
  const api = useApi(WaitingListApi, csrfToken);
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
            loading={loading}
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
              loading={loading}
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
