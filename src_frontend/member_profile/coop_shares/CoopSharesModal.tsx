import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import { useApi } from "../../hooks/useApi.ts";
import { BestellWizardApi, CoopApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { formatCurrency } from "../../utils/formatCurrency.ts";
import { handleRequestError } from "../../utils/handleRequestError.ts";

interface CoopSharesModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  onSharesPurchased: () => void;
  currentNumberOfShares: number;
}

const CoopSharesModal: React.FC<CoopSharesModalProps> = ({
  memberId,
  csrfToken,
  show,
  onHide,
  onSharesPurchased,
  currentNumberOfShares,
}) => {
  const coopApi = useApi(CoopApi, csrfToken);
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);
  const [loading, setLoading] = useState(true);
  const [priceOfAShare, setPriceOfAShare] = useState(0);
  const [numberOfShares, setNumberOfShares] = useState(1);
  const [statuteLink, setStatuteLink] = useState("");
  const [statuteAccepted, setStatuteAccepted] = useState(false);
  const [organizationName, setOrganizationName] = useState("");

  useEffect(() => {
    setStatuteAccepted(false);

    if (!show) return;

    setLoading(true);

    bestellWizardApi
      .bestellWizardApiBestellWizardBaseDataRetrieve()
      .then((response) => {
        setPriceOfAShare(response.priceOfAShare);
        setStatuteLink(response.coopStatuteLink);
        setOrganizationName(response.organizationName);
      })
      .catch((error) =>
        handleRequestError(error, "Fehler beim Laden der Preis einen Anteil"),
      )
      .finally(() => setLoading(false));
  }, [show]);

  function onConfirmPurchase() {
    setLoading(true);

    coopApi
      .coopApiExistingMemberPurchasesSharesCreate({
        memberId: memberId,
        numberOfSharesToAdd: numberOfShares,
      })
      .then(() => onSharesPurchased())
      .catch((error) => handleRequestError(error, "Fehler beim Zeichnen"))
      .finally(() => setLoading(false));
  }

  return (
    <Modal onHide={onHide} show={show} size={"lg"}>
      <Modal.Header>Genossenschaftsanteile zeichnen</Modal.Header>
      <Modal.Body>
        <p>
          Du besitzt gerade {currentNumberOfShares} Genossenschaftsanteile. Wie
          viel willst du zusätzlich zeichnen?
        </p>
        <div className={"d-flex flex-row align-items-center gap-2"}>
          <Form.Group style={{ maxWidth: "65px" }}>
            <Form.Control
              type={"number"}
              min={1}
              step={1}
              value={numberOfShares}
              onChange={(event) =>
                setNumberOfShares(parseInt(event.target.value))
              }
            />
          </Form.Group>
          <span> x {formatCurrency(priceOfAShare)} = </span>
          <span>
            <strong>{formatCurrency(numberOfShares * priceOfAShare)}</strong>{" "}
            einmalige Genossenschaftsanteile
          </span>
        </div>
        <div className={"mt-2"}>
          <Form.Check
            id={"statute"}
            checked={statuteAccepted}
            onChange={(event) => setStatuteAccepted(event.target.checked)}
            label={
              "Ich habe die Satzung der " +
              organizationName +
              " zur Kenntnis genommen."
            }
          />
          <Form.Text>
            <a href={statuteLink}>{statuteLink}</a>
          </Form.Text>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          variant={"primary"}
          text={"Zeichnen"}
          loading={loading}
          icon={"contract"}
          disabled={!statuteAccepted}
          onClick={onConfirmPurchase}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default CoopSharesModal;
