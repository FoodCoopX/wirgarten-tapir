import React, { useEffect } from "react";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Col, Form, Row } from "react-bootstrap";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";

interface BestellWizardCoopSharesProps {
  selectedNumberOfCoopShares: number;
  setSelectedNumberOfCoopShares: (nbShares: number) => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
  minimumNumberOfShares: number;
  waitingListModeEnabled: boolean;
  studentStatusEnabled: boolean;
  setStudentStatusEnabled: (status: boolean) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
  settings: BestellWizardSettings;
}

const BestellWizardCoopShares: React.FC<BestellWizardCoopSharesProps> = ({
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  statuteAccepted,
  setStatuteAccepted,
  minimumNumberOfShares,
  waitingListModeEnabled,
  studentStatusEnabled,
  setStudentStatusEnabled,
  waitingListLinkConfirmationModeEnabled,
  settings,
}) => {
  useEffect(() => {
    if (!studentStatusEnabled) {
      return;
    }

    setSelectedNumberOfCoopShares(0);
    setStatuteAccepted(false);
  }, [studentStatusEnabled]);

  return (
    <>
      <Row>
        <Col>
          <span dangerouslySetInnerHTML={{ __html: settings.coopStepText }} />
          <BestellWizardCardSubtitle
            text={
              "Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem Biotop beteiligen?"
            }
          />
          <p>
            Du musst mindestens {minimumNumberOfShares} Genossenschaftsanteil zu{" "}
            {formatCurrency(settings.priceOfAShare)} erwerben.
          </p>
        </Col>
      </Row>
      <Row>
        <Col>
          <div className={"d-flex flex-row align-items-center gap-2"}>
            <Form.Group style={{ maxWidth: "65px" }}>
              <Form.Control
                type={"number"}
                min={minimumNumberOfShares}
                step={1}
                value={selectedNumberOfCoopShares}
                onChange={(event) =>
                  setSelectedNumberOfCoopShares(parseInt(event.target.value))
                }
                disabled={studentStatusEnabled}
              />
            </Form.Group>
            <span> x {formatCurrency(settings.priceOfAShare)} = </span>
            <span>
              <strong>
                {formatCurrency(
                  selectedNumberOfCoopShares * settings.priceOfAShare,
                )}
              </strong>{" "}
              einmalige Genossenschaftsanteile
            </span>
          </div>
        </Col>
      </Row>
      {!waitingListModeEnabled && (
        <>
          <Row className={"mt-2"}>
            <Col>
              <Form.Check
                id={"statute"}
                checked={statuteAccepted}
                onChange={(event) => setStatuteAccepted(event.target.checked)}
                label={
                  "Ich habe die Satzung der Biotop Oberland eG und die Kündigungsfrist von 2 Monaten zum Jahresende zur Kenntnis genommen."
                }
                disabled={studentStatusEnabled}
              />
              <Form.Text>
                <a href={"https://biotop-oberland.de/satzung"}>
                  https://biotop-oberland.de/satzung
                </a>
                <br />
                Bitte beachte, dass deine Genossenschaftsanteile erst bei
                Austritt aus der Genossenschaft und nach Verabschiedung des
                Jahresabschlusses im Folgejahr zurückgezahlt werden dürfen.
                Siehe dazu Satzung § 10 und § 37.
              </Form.Text>
              <Form.Text></Form.Text>
            </Col>
          </Row>
          {settings.studentStatusAllowed && (
            <Row>
              <Col>
                <Form.Check
                  label={
                    "Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen"
                  }
                  checked={studentStatusEnabled}
                  onChange={(event) =>
                    setStudentStatusEnabled(event.target.checked)
                  }
                  disabled={waitingListLinkConfirmationModeEnabled}
                  id={"student"}
                />
                <Form.Text>
                  Die Immatrikulationsbescheinigung muss per Mail an{" "}
                  <a href="mailto:lueneburg@wirgarten.com">
                    lueneburg@wirgarten.com
                  </a>{" "}
                  gesendet werden.
                </Form.Text>
              </Col>
            </Row>
          )}
        </>
      )}
    </>
  );
};

export default BestellWizardCoopShares;
