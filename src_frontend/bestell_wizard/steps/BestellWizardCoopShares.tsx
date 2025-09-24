import React, { useEffect } from "react";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { Col, Form, Row } from "react-bootstrap";
import BestellWizardCardSubtitle from "../components/BestellWizardCardSubtitle.tsx";
import { BestellWizardSettings } from "../types/BestellWizardSettings.ts";
import { ShoppingCart } from "../types/ShoppingCart.ts";
import TapirButton from "../../components/TapirButton.tsx";
import { PublicProductType } from "../../api-client";
import { areAllOrderedProductsInWaitingList } from "../utils/areAllOrderedProductsInWaitingList.ts";

interface BestellWizardCoopSharesProps {
  selectedNumberOfCoopShares: number;
  setSelectedNumberOfCoopShares: (nbShares: number) => void;
  statuteAccepted: boolean;
  setStatuteAccepted: (statuteRead: boolean) => void;
  minimumNumberOfShares: number;
  studentStatusEnabled: boolean;
  setStudentStatusEnabled: (status: boolean) => void;
  waitingListLinkConfirmationModeEnabled: boolean;
  settings: BestellWizardSettings;
  becomeMemberNow: boolean | null;
  setBecomeMemberNow: (becomeMemberNow: boolean) => void;
  shoppingCart: ShoppingCart;
  productsTypesInWaitingList: Set<PublicProductType>;
}

const BestellWizardCoopShares: React.FC<BestellWizardCoopSharesProps> = ({
  selectedNumberOfCoopShares,
  setSelectedNumberOfCoopShares,
  statuteAccepted,
  setStatuteAccepted,
  minimumNumberOfShares,
  studentStatusEnabled,
  setStudentStatusEnabled,
  waitingListLinkConfirmationModeEnabled,
  settings,
  becomeMemberNow,
  setBecomeMemberNow,
  shoppingCart,
  productsTypesInWaitingList,
}) => {
  useEffect(() => {
    if (!studentStatusEnabled) {
      return;
    }

    setSelectedNumberOfCoopShares(0);
    setStatuteAccepted(false);
  }, [studentStatusEnabled]);

  function shouldConfirmMemberNow() {
    if (becomeMemberNow !== null) {
      return false;
    }

    if (settings.forceWaitingList) {
      return false;
    }

    return areAllOrderedProductsInWaitingList(
      shoppingCart,
      productsTypesInWaitingList,
    );
  }

  return shouldConfirmMemberNow() ? (
    <>
      <Row>
        <Col>
          <BestellWizardCardSubtitle
            text={"Möchtest du sofort Mitglied werden?"}
          />
          <p>
            Die wirst auf die Warteliste für deine Bestellung eingetragen. Du
            kannst dich aber entscheiden sofort Mitglied der Genossenschaft zu
            werden.
          </p>
        </Col>
      </Row>
      <Row>
        <Col className={"d-flex flex-column align-items-center"}>
          <TapirButton
            text={"Sofort Mitglied werden"}
            variant={"outline-primary"}
            onClick={() => setBecomeMemberNow(true)}
          />
          <div className={"text-center"}>
            Deine Bestellung geht auf der Warteliste bis ein Platz für dich frei
            wird. Du kaufst aber gleich Genossenschaftsanteile. Du wirst sofort
            Mitglied der Genossenschaft.
          </div>
        </Col>
        <Col className={"d-flex flex-column align-items-center"}>
          <TapirButton
            text={"Erst Mitglied werden wenn die Bestellung bestätigt wird"}
            variant={"outline-primary"}
            onClick={() => setBecomeMemberNow(false)}
          />
          <div className={"text-center"}>
            Deine Bestellung geht auf der Warteliste bis ein Platz für dich frei
            wird. Erst wenn ein Platz für dich frei wird kaufst du
            Genossenschaftsanteile. Erst dann wirst du Mitglied der
            Genossenschaft.
          </div>
        </Col>
      </Row>
    </>
  ) : (
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
      <Row className={"mt-2"}>
        <Col>
          <Form.Check
            id={"statute"}
            checked={statuteAccepted}
            onChange={(event) => setStatuteAccepted(event.target.checked)}
            label={
              "Ich habe die Satzung der" +
              settings.organizationName +
              " und die Kündigungsfrist von 2 Monaten zum Jahresende zur Kenntnis genommen."
            }
            disabled={studentStatusEnabled}
          />
          <Form.Text>
            <a href={settings.coopStatuteLink}>{settings.coopStatuteLink}</a>
            <br />
            Bitte beachte, dass deine Genossenschaftsanteile erst bei Austritt
            aus der Genossenschaft und nach Verabschiedung des Jahresabschlusses
            im Folgejahr zurückgezahlt werden dürfen. Siehe dazu Satzung § 10
            und § 37.
          </Form.Text>
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
  );
};

export default BestellWizardCoopShares;
