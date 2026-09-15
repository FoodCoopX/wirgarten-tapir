import React, { useEffect, useState } from "react";
import { Modal, Table } from "react-bootstrap";
import { MemberWithoutIban, PaymentsApi } from "../api-client";
import PlaceholderTableRows from "../components/PlaceholderTableRows.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface MembersWithoutIbanModalProps {
  show: boolean;
  onHide: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const MembersWithoutIbanModal: React.FC<MembersWithoutIbanModalProps> = ({
  show,
  onHide,
  setToastDatas,
}) => {
  const api = useApi(PaymentsApi, "unused");
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<MemberWithoutIban[]>([]);

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);
    api
      .paymentsApiMembersWithoutIbanList()
      .then((response) => setMembers(response))
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Benutzer ohne IBAN",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  return (
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <Modal.Title>Benutzer ohne IBAN</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Table responsive hover striped bordered>
          <thead>
            <tr>
              <th>Vorname</th>
              <th>Nachname</th>
              <th>E-Mail</th>
              <th>Telefonnummer</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <PlaceholderTableRows nbRows={10} nbColumns={4} size={"lg"} />
            ) : (
              members.map((member, index) => (
                <tr key={index}>
                  <td>{member.firstName}</td>
                  <td>{member.lastName}</td>
                  <td>{member.email}</td>
                  <td>{member.phoneNumber}</td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default MembersWithoutIbanModal;
