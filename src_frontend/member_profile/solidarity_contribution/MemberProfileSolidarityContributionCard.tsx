import React, { useEffect, useState } from "react";
import { Card, Form, Modal, Spinner } from "react-bootstrap";
import "dayjs/locale/de";
import {
  SolidarityContribution,
  SolidarityContributionApi,
} from "../../api-client";
import { useApi } from "../../hooks/useApi.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { formatDateNumeric } from "../../utils/formatDateNumeric.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { getCsrfToken } from "../../utils/getCsrfToken.ts";

interface MemberProfileSolidarityContributionCardProps {
  memberId: string;
  adminEmail: string;
}

const MemberProfileSolidarityContributionCard: React.FC<
  MemberProfileSolidarityContributionCardProps
> = ({ memberId, adminEmail }) => {
  const api = useApi(SolidarityContributionApi, getCsrfToken());
  const [loading, setLoading] = useState(true);
  const [solidarityContributions, setSolidarityContributions] = useState<
    SolidarityContribution[]
  >([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [newContributionAsString, setNewContributionAsStringAsString] =
    useState("0");
  const [showValidation, setShowValidation] = useState(false);
  const [changeValidFrom, setChangeValidFrom] = useState(new Date());
  const [userCanSetLowerValue, setUserCanSetLowerValue] = useState(false);

  useEffect(() => {
    setLoading(true);

    api
      .solidarityContributionApiMemberSolidarityContributionsRetrieve({
        memberId: memberId,
      })
      .then((response) => {
        setSolidarityContributions(response.contributions);
        setChangeValidFrom(response.changeValidFrom);
        setUserCanSetLowerValue(response.userCanSetLowerValue);
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Laden der Solidarbeitrag.",
        );
      })
      .finally(() => setLoading(false));
  }, [memberId]);

  useEffect(() => {
    const current = getCurrentContribution();
    if (current) {
      setNewContributionAsStringAsString(current.amount);
    } else if (solidarityContributions.length > 0) {
      setNewContributionAsStringAsString(
        solidarityContributions[solidarityContributions.length - 1].amount,
      );
    } else {
      setNewContributionAsStringAsString("0");
    }
  }, [solidarityContributions]);

  useEffect(() => {
    setShowValidation(false);
  }, [modalOpen]);

  function onConfirm() {
    setShowValidation(true);

    if (!newValueIsValid()) {
      return;
    }

    setLoading(true);

    api
      .solidarityContributionApiUpdateMemberContributionCreate({
        soliSerializerRequest: {
          memberId: memberId,
          amount: parseFloat(newContributionAsString),
        },
      })
      .then((contributions) => {
        setSolidarityContributions(contributions);
        setModalOpen(false);
      })
      .catch(async (error) => {
        await handleRequestError(
          error,
          "Fehler beim Speichern der Solidarbeitrag.",
        );
      })
      .finally(() => setLoading(false));
  }

  function shouldShowWarningLowerValue() {
    if (userCanSetLowerValue) {
      return false;
    }

    const newContributionAsFloat = parseFloat(newContributionAsString);
    if (isNaN(newContributionAsFloat)) {
      return false;
    }

    let currentContributionAsFloat = 0;
    const current = getCurrentContribution();
    if (current) {
      currentContributionAsFloat = parseFloat(current.amount);
    }

    return newContributionAsFloat < currentContributionAsFloat;
  }

  function getCurrentContribution() {
    for (const contribution of solidarityContributions) {
      const today = new Date();
      if (contribution.startDate < today && today < contribution.endDate) {
        return contribution;
      }
    }
  }

  function buildCurrentContribution() {
    const contribution = getCurrentContribution();
    const amount = contribution
      ? formatCurrency(parseFloat(contribution.amount))
      : "Kein Beitrag";

    return "Aktueller Beitrag: " + amount;
  }

  function buildFutureContributions() {
    const today = new Date();
    const futureContributions = solidarityContributions.filter(
      (contribution) => contribution.startDate > today,
    );

    if (futureContributions.length === 0) {
      return;
    }

    return futureContributions.map((contribution) => (
      <span key={contribution.id}>
        <br />
        <span>
          Ab dem {formatDateNumeric(contribution.startDate)}:{" "}
          {formatCurrency(parseFloat(contribution.amount))}
        </span>
      </span>
    ));
  }

  function newValueIsValid() {
    const newContributionAsFloat = parseFloat(newContributionAsString);
    if (isNaN(newContributionAsFloat)) {
      return false;
    }

    return !shouldShowWarningLowerValue();
  }

  function buildContent() {
    if (loading)
      return (
        <Card>
          <Card.Header>
            <h5 className={"mb-0"}>Solidarbeitrag</h5>
          </Card.Header>
          <Card.Body>
            <Spinner />
          </Card.Body>
        </Card>
      );

    return (
      <>
        <Card>
          <Card.Header>
            <span
              className={"d-flex justify-content-between align-items-center"}
            >
              <h5 className={"mb-0"}>Solidarbeitrag</h5>
              <TapirButton
                variant={"outline-primary"}
                icon={"edit"}
                text={"Beitrag anpassen"}
                onClick={() => setModalOpen(true)}
              />
            </span>
          </Card.Header>
          <Card.Body>
            {buildCurrentContribution()}
            {buildFutureContributions()}
          </Card.Body>
        </Card>
        <Modal
          show={modalOpen}
          centered={true}
          onHide={() => setModalOpen(false)}
        >
          <Modal.Header closeButton={true}>
            Solidarbeitrag anpassen
          </Modal.Header>
          <Modal.Body>
            <Form.Group>
              <Form.Label>Neuer Beitrag (€)</Form.Label>
              <Form.Control
                type={"number"}
                step={0.01}
                value={newContributionAsString}
                onChange={(event) =>
                  setNewContributionAsStringAsString(event.target.value)
                }
                isInvalid={showValidation && !newValueIsValid()}
                isValid={showValidation && newValueIsValid()}
              />
              {showValidation && isNaN(parseFloat(newContributionAsString)) && (
                <>
                  <Form.Text className={"text-danger"}>
                    Ungültiger Zahl
                  </Form.Text>
                  <br />
                </>
              )}
              {showValidation && shouldShowWarningLowerValue() && (
                <>
                  <Form.Text className={"text-danger"}>
                    Du kannst deinen Beitrag nicht selber nach Unten anpassen.
                    Kontaktiere bitte {adminEmail}
                  </Form.Text>
                  <br />
                </>
              )}
              <Form.Text>
                Neuer Beitrag gültig ab dem {formatDateNumeric(changeValidFrom)}
              </Form.Text>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <span
              className={"d-flex justify-content-between align-items-center"}
              style={{ width: "100%" }}
            >
              <TapirButton
                variant={"outline-secondary"}
                onClick={() => setModalOpen(false)}
                icon={"cancel"}
                text={"Abbrechen"}
              />
              <TapirButton
                variant={"primary"}
                onClick={onConfirm}
                icon={"save"}
                text={"Anpassung bestätigen"}
                loading={loading}
              />
            </span>
          </Modal.Footer>
        </Modal>
      </>
    );
  }
  return buildContent();
};

export default MemberProfileSolidarityContributionCard;
