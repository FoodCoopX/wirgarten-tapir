import React, { useState } from "react";
import { Modal } from "react-bootstrap";
import { useApi } from "../hooks/useApi.ts";
import { MemberDataToConfirm, SubscriptionsApi } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";

interface ContractUpdatesConfirmationCardProps {
  csrfToken: string;
  changes: MemberDataToConfirm;
  show: boolean;
  onHide: () => void;
}

const ContractUpdatesConfirmationCard: React.FC<
  ContractUpdatesConfirmationCardProps
> = ({ csrfToken, changes, show, onHide }) => {
  const subscriptionsApi = useApi(SubscriptionsApi, csrfToken);
  const [loading, setLoading] = useState(false);

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>
          Änderung bestätigen: {changes.member.firstName}{" "}
          {changes.member.lastName} #{changes.member.memberNo}
        </h5>
      </Modal.Header>
      <Modal.Body>SALUT</Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Bestätigen"}
          variant={"primary"}
          loading={loading}
          onClick={() => alert("TODO")}
          icon={"contract_edit"}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default ContractUpdatesConfirmationCard;
