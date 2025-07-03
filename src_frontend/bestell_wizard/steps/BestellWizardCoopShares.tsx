import React, { useEffect } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Col, Form, Row } from "react-bootstrap";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";

interface BestellWizardCoopSharesProps {
  theme: TapirTheme;
  selectedNumberOfCoopShares: number;
  setSelectedNumberOfCoopShares: (nbShares: number) => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
  minimumNumberOfShares: number;
  priceOfAShare: number;
  waitingListModeEnabled: boolean;
  studentStatusAllowed: boolean;
  studentStatusEnabled: boolean;
  setStudentStatusEnabled: (status: boolean) => void;
}

const BestellWizardCoopShares: React.FC<BestellWizardCoopSharesProps> = ({
  theme,
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  statuteAccepted,
  setStatuteAccepted,
  minimumNumberOfShares,
  priceOfAShare,
  waitingListModeEnabled,
  studentStatusAllowed,
  studentStatusEnabled,
  setStudentStatusEnabled,
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
          <BestellWizardCardTitle text={"Mitglied der Genossenschaft"} />
          <p>
            Als Mitglied unserer Genossenschaft bist du gleichzeitig
            MiteigentümerIn deiner eigenen Gemüsegärtnerei und deines regionalen
            Selbstbedienungsladens! Du kannst somit bei allen
            Grundsatzentscheidungen mitbestimmen und hast ein Stimmrecht bei der
            Generalversammlung.
          </p>
          <p>
            Mit deinen Genossenschaftsanteilen ermöglichst du die gemeinsame
            Finanzierung wichtiger Investitionen für die Genossenschaft.
          </p>
          <p>
            Weitere Infos zur Mitgliedschaft findest du hier:{" "}
            <a href={"https://biotop-oberland.de/gebuehrenordnung"}>
              https://biotop-oberland.de/gebuehrenordnung
            </a>
            <br />
            Warum eine Genossenschaft? Details dazu findest du hier:{" "}
            <a href={"https://biotop-oberland.de/so-gehts/"}>
              https://biotop-oberland.de/so-gehts/
            </a>
          </p>
          <BestellWizardCardSubtitle
            text={
              "Mit wie vielen Genossenschaftsanteilen möchtest du dich an deinem Biotop beteiligen?"
            }
          />
          <p>
            Du musst mindestens {minimumNumberOfShares} Genossenschaftsanteil zu{" "}
            {formatCurrency(priceOfAShare)} erwerben.
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
            <span>
              <strong>
                {formatCurrency(selectedNumberOfCoopShares * priceOfAShare)}
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
          {studentStatusAllowed && (
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
