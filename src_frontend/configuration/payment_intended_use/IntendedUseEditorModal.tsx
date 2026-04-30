import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Container,
  Form,
  Modal,
  ModalTitle,
  Row,
  Spinner,
  Table,
} from "react-bootstrap";
import { Member, Payment, PaymentsApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { useApi } from "../../hooks/useApi.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface IntendedUseEditorModalProps {
  show: boolean;
  onHide: () => void;
  isContract: boolean;
  title: string;
  outerPattern: string;
  setOuterPattern: (p: string) => void;
}

function buildPreview(preview: string) {
  return preview.split("\n").map((line, index) => (
    <span key={index}>
      {line}
      <br />
    </span>
  ));
}

const IntendedUseEditorModal: React.FC<IntendedUseEditorModalProps> = ({
  show,
  onHide,
  isContract,
  title,
  outerPattern,
  setOuterPattern,
}) => {
  const paymentsApi = useApi(PaymentsApi, "unused");
  const [loading, setLoading] = useState(false);
  const [innerPreviews, setInnerPreviews] = useState<string[]>([]);
  const [outerPreviews, setOuterPreviews] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [tokens, setTokens] = useState<string[]>([]);
  const [innerPattern, setInnerPattern] = useState("");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const innerInputFieldRef = useRef<HTMLTextAreaElement>(null);

  function onChange(event: React.ChangeEvent<HTMLInputElement>) {
    setInnerPattern(event.target.value);
  }

  useEffect(() => {
    if (!show) {
      return;
    }

    setInnerPattern(outerPattern);
  }, [show]);

  useEffect(() => {
    if (!show) {
      return;
    }
    fetchPreviews();
  }, [innerPattern, show]);

  function fetchPreviews() {
    setLoading(true);

    const requestData = {
      patternOld: outerPattern,
      patternNew: innerPattern,
    };

    let promise;
    if (isContract) {
      promise =
        paymentsApi.paymentsApiIntendedUsePreviewContractsRetrieve(requestData);
    } else {
      promise =
        paymentsApi.paymentsApiIntendedUsePreviewCoopSharesRetrieve(
          requestData,
        );
    }
    promise
      .then((response) => {
        setInnerPreviews(response.previewsNew);
        setOuterPreviews(response.previewsOld);
        setError(response.error);
        setTokens(response.tokens);
        setPayments(response.payments);
        setMembers(response.members);
      })
      .catch((error) => {
        handleRequestError(
          error,
          "Fehler beim Laden der Vorschau für Verwendungszwecke",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }

  function buildPreviews() {
    if (error) {
      return <Alert variant={"warning"}>{error}</Alert>;
    }

    return (
      <Table responsive striped bordered>
        <thead>
          <tr>
            <th>{loading ? <Spinner size={"sm"} /> : "Zahlung"}</th>
            <th>Mitglied</th>
            <th>Vorschau Alt</th>
            <th>Vorschau Neu</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member, index) => (
            <tr key={member.id!}>
              <td>
                {formatCurrency(payments[index].amount)},{" "}
                {formatDateNumeric(
                  payments[index].subscriptionPaymentRangeStart,
                )}
              </td>
              <td>
                {member.firstName} {member.lastName} #{member.memberNo}
              </td>
              <td>{buildPreview(outerPreviews[index])}</td>
              <td>{buildPreview(innerPreviews[index])}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4}>
              <TapirButton
                icon={"refresh"}
                text={"Andere Vorschau laden"}
                variant={"outline-secondary"}
                size={"sm"}
                onClick={() => {
                  fetchPreviews();
                }}
              />
            </td>
          </tr>
        </tfoot>
      </Table>
    );
  }

  function onTokenClicked(token: string) {
    if (!innerInputFieldRef.current) {
      return;
    }

    const before = innerPattern.slice(
      0,
      innerInputFieldRef.current.selectionStart,
    );
    const after = innerPattern.slice(
      innerInputFieldRef.current.selectionStart,
      innerPattern.length,
    );

    setInnerPattern(before + "{" + token + "}" + after);
  }

  return (
    <Modal show={show} onHide={onHide} centered={false} size={"xl"}>
      <Modal.Header closeButton={true}>
        <span
          className={"d-flex justify-content-between"}
          style={{ width: "100%" }}
        >
          <ModalTitle>{title}</ModalTitle>
          <TapirButton
            icon={"check"}
            text={"Verwenden"}
            onClick={() => {
              setOuterPattern(innerPattern);
              onHide();
            }}
            variant={"outline-secondary"}
          />
        </span>
      </Modal.Header>
      <Modal.Body>
        <div className={"mb-2"}>
          <Form.Control
            value={innerPattern}
            onChange={onChange}
            as={"textarea"}
            rows={4}
            ref={innerInputFieldRef}
          />
        </div>
        <Container>
          <Row>
            <div className={"d-flex flex-row gap-2 flex-wrap"}>
              {tokens.map((token) => (
                <span key={token}>
                  <TapirButton
                    icon={"new_label"}
                    size={"sm"}
                    variant={"outline-secondary"}
                    text={token}
                    onClick={() => {
                      onTokenClicked(token);
                    }}
                  />
                </span>
              ))}
            </div>
          </Row>
          <Row className={"mt-4"}>{buildPreviews()}</Row>
        </Container>
      </Modal.Body>
    </Modal>
  );
};

export default IntendedUseEditorModal;
