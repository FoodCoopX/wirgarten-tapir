import React, { useEffect, useState } from "react";
import { TapirTheme } from "../../types/TapirTheme.ts";
import { CoopApi } from "../../api-client";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Col, Form, Row } from "react-bootstrap";
import { useApi } from "../../hooks/useApi.ts";
import BestellWizardCardTitle from "../components/BestellWizardCardTitle.tsx";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";

interface BestellWizardCoopSharesProps {
  theme: TapirTheme;
  shoppingCart: ShoppingCart;
  selectedNumberOfCoopShares: number;
  setSelectedNumberOfCoopShares: (nbShares: number) => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
}

const BestellWizardCoopShares: React.FC<BestellWizardCoopSharesProps> = ({
  theme,
  shoppingCart,
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  statuteAccepted,
  setStatuteAccepted,
}) => {
  const coopApi = useApi(CoopApi, "unused");
  const [minimumNumberOfShares, setMinimumNumberOfShares] = useState(0);
  const [priceOfAShare, setPriceOfAShare] = useState(0);

  useEffect(() => {
    coopApi
      .coopApiMinimumNumberOfSharesRetrieve({
        productIds: Object.keys(shoppingCart),
        quantities: Object.values(shoppingCart),
      })
      .then((response) => {
        setMinimumNumberOfShares(response.minimumNumberOfShares);
        setPriceOfAShare(response.priceOfAShare);
        if (selectedNumberOfCoopShares < response.minimumNumberOfShares) {
          setSelectedNumberOfCoopShares(response.minimumNumberOfShares);
        }
      });
  }, [shoppingCart]);

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
      <Row className={"mt-2"}>
        <Col>
          <Form.Check
            id={"statute"}
            checked={statuteAccepted}
            onChange={(event) => setStatuteAccepted(event.target.checked)}
            label={
              "Ich habe die Satzung der Biotop Oberland eG und die Kündigungsfrist von 2 Monaten zum Jahresende zur Kenntnis genommen."
            }
          />
          <Form.Text>
            <a href={"https://biotop-oberland.de/satzung"}>
              https://biotop-oberland.de/satzung
            </a>
          </Form.Text>
        </Col>
      </Row>
      <Row className={"mt-2"}>
        <Col>
          <p>
            Bitte beachte, dass Deine Genossenschaftsanteile erst bei Austritt
            aus der Genossenschaft und nach Verabschiedung des Jahresabschlusses
            im Folgejahr zurückgezahlt werden dürfen. Siehe dazu Satzung § 10
            und § 37.
          </p>
        </Col>
      </Row>
    </>
  );
};

export default BestellWizardCoopShares;
