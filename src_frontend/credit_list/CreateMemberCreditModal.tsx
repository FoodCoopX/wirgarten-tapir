import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import TapirButton from "../components/TapirButton.tsx";
import { ToastData } from "../types/ToastData.ts";
import dayjs from "dayjs";
import { CoopApi, Member, PaymentsApi } from "../api-client";
import { useApi } from "../hooks/useApi.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface CreateMemberCreditModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  onCreditCreated: () => void;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const CreateMemberCreditModal: React.FC<CreateMemberCreditModalProps> = ({
  show,
  onHide,
  csrfToken,
  onCreditCreated,
  setToastDatas,
}) => {
  const [loading, setLoading] = useState(false);
  const [dueDate, setDueDate] = useState<Date>(new Date());
  const [memberId, setMemberId] = useState<string>();
  const [members, setMembers] = useState<Member[]>([]);
  const [amount, setAmount] = useState(0.01);
  const [purpose, setPurpose] = useState("");
  const [comment, setComment] = useState("");
  const coopApi = useApi(CoopApi, csrfToken);
  const paymentsApi = useApi(PaymentsApi, csrfToken);

  useEffect(() => {
    if (!show) {
      return;
    }

    setLoading(true);
    coopApi
      .coopMembersList()
      .then((members) => {
        members.sort((a, b) => a.lastName.localeCompare(b.lastName));
        setMembers(members);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Gutschriften",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onCreate() {
    setLoading(true);

    if (memberId === undefined) {
      alert("Kein Mitglied ausgewählt");
      return;
    }

    paymentsApi
      .paymentsApiMemberCreditCreateCreate({
        memberCreditCreateRequest: {
          memberId: memberId,
          purpose: purpose,
          comment: comment,
          dueDate: dueDate,
          amount: amount,
        },
      })
      .then(() => {
        onHide();
        onCreditCreated();
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Erzeugen des Gutschrift",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Gutschrift erzeugen</h5>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group>
            <Form.Label>Fälligkeitsdatum</Form.Label>
            <Form.Control
              type={"date"}
              onChange={(event) => setDueDate(new Date(event.target.value))}
              required={true}
              value={dayjs(dueDate).format("YYYY-MM-DD")}
            />
          </Form.Group>
          <Form.Group className={"mt-2"}>
            <Form.Label>Mitglied</Form.Label>
            <Form.Select
              value={memberId}
              onChange={(event) => setMemberId(event.target.value)}
            >
              <option value={undefined}>Mitglied auswählen</option>
              {members.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.lastName} {member.firstName} #{member.memberNo}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className={"mt-2"}>
            <Form.Label>Wert (€)</Form.Label>
            <Form.Control
              type={"number"}
              step={0.01}
              min={0.01}
              value={amount}
              onChange={(event) => setAmount(parseFloat(event.target.value))}
            />
          </Form.Group>
          <Form.Group className={"mt-2"}>
            <Form.Label>Verwendungszweck</Form.Label>
            <Form.Control
              value={purpose}
              onChange={(event) => setPurpose(event.target.value)}
              placeholder={"Verwendungszweck"}
            />
          </Form.Group>
          <Form.Group className={"mt-2"}>
            <Form.Label>Kommentar</Form.Label>
            <Form.Control
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder={"Kommentar"}
            />
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Gutschrift erzeugen"}
          icon={"save"}
          variant={"primary"}
          onClick={onCreate}
          loading={loading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default CreateMemberCreditModal;
