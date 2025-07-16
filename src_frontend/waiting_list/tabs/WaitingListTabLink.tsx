import React, { useState } from "react";
import { Col, Row } from "react-bootstrap";
import { WaitingListApi, WaitingListEntryDetails } from "../../api-client";
import { formatDateText } from "../../utils/formatDateText.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { ToastData } from "../../types/ToastData.ts";
import { v4 as uuidv4 } from "uuid";

interface WaitingListTabLinkProps {
  entryDetails: WaitingListEntryDetails;
  csrfToken: string;
  reloadEntries: () => void;
  addToast: (data: ToastData) => void;
}

const WaitingListTabLink: React.FC<WaitingListTabLinkProps> = ({
  entryDetails,
  csrfToken,
  reloadEntries,
  addToast,
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
        addToast({
          title: "Mail versendet",
          variant: "success",
          id: uuidv4(),
        });
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim versenden der Mail", addToast),
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
        addToast({
          title: "Link ausgeschaltet",
          variant: "success",
          id: uuidv4(),
        });
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim ausschalten der Link", addToast),
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
            <span className={"material-icons"}>warning</span> Es muss maximal 1
            Verteilstation-Wunsch geben um den Link zu versenden (ggf. muss
            einmal gespeichert werden).
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
      </Col>
    </Row>
  );
};

export default WaitingListTabLink;
