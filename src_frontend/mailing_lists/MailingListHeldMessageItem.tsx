import React from "react";
import { ListGroup } from "react-bootstrap";
import { MailingListHeldMessage } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { formatDateNumeric } from "../utils/formatDateNumeric.ts";

interface MailingListHeldMessageItemProps {
  heldMessage: MailingListHeldMessage;
  loading: boolean;
  disabled: boolean;
  onAccept: () => void;
  onReject: () => void;
  onDiscard: () => void;
}

const MailingListHeldMessageItem: React.FC<MailingListHeldMessageItemProps> = ({
  heldMessage,
  loading,
  disabled,
  onAccept,
  onReject,
  onDiscard,
}) => {
  function buildSender() {
    if (!heldMessage.senderName) {
      return heldMessage.sender;
    }

    let name = heldMessage.senderName;
    if (heldMessage.formattedMemberNumber) {
      name += " #" + heldMessage.formattedMemberNumber;
    }

    let nameOrLink;
    if (heldMessage.linkToMemberProfile) {
      nameOrLink = <a href={heldMessage.linkToMemberProfile}>{name}</a>;
    } else {
      nameOrLink = name;
    }

    return (
      <>
        {nameOrLink} ({heldMessage.sender})
      </>
    );
  }

  return (
    <ListGroup.Item>
      <div className={"d-flex justify-content-between gap-2"}>
        <div>
          <h6 className={"mb-1"}>{heldMessage.subject || "(Kein Betreff)"}</h6>
          <div>
            Von {buildSender()}, am{" "}
            {formatDateNumeric(heldMessage.holdDate, true)}
          </div>
          <small className={"text-muted"}>{heldMessage.reason}</small>
        </div>
        <span className={"d-flex gap-2 align-items-start"}>
          <TapirButton
            variant={"outline-success"}
            size={"sm"}
            icon={"check"}
            text={"Freigeben"}
            onClick={onAccept}
            loading={loading}
            disabled={disabled}
          />
          <TapirButton
            variant={"outline-danger"}
            size={"sm"}
            icon={"block"}
            text={"Ablehnen"}
            onClick={onReject}
            disabled={disabled}
          />
          <TapirButton
            variant={"outline-danger"}
            size={"sm"}
            icon={"delete"}
            text={"Verwerfen"}
            onClick={onDiscard}
            disabled={disabled}
          />
        </span>
      </div>
      <pre
        className={"mt-2 mb-0 p-2 border rounded bg-body-tertiary"}
        style={{ whiteSpace: "pre-wrap", maxHeight: "300px" }}
      >
        {heldMessage.body}
      </pre>
    </ListGroup.Item>
  );
};

export default MailingListHeldMessageItem;
