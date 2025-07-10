import React from "react";
import { Col, Row } from "react-bootstrap";
import { WaitingListEntryDetails } from "../../api-client";
import { formatDateText } from "../../utils/formatDateText.ts";
import TapirButton from "../../components/TapirButton.tsx";

interface WaitingListTabLinkProps {
  entryDetails: WaitingListEntryDetails;
}

const WaitingListTabLink: React.FC<WaitingListTabLinkProps> = ({
  entryDetails,
}) => {
  return (
    <Row>
      <Col className={"mt-2"}>
        {entryDetails.linkSentDate ? (
          <p>Link geschickt am {formatDateText(entryDetails.linkSentDate)}</p>
        ) : (
          <p>Link nicht geschickt</p>
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
          />
        </p>
        {entryDetails.linkSentDate && (
          <p>
            <TapirButton
              variant={"danger"}
              text={"Link ausschalten"}
              icon={"link_off"}
            />
          </p>
        )}
      </Col>
    </Row>
  );
};

export default WaitingListTabLink;
