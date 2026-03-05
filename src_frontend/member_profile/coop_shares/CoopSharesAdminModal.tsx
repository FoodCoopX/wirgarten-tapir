import React, { useEffect, useState } from "react";
import { Form, Modal, OverlayTrigger, Popover } from "react-bootstrap";
import "dayjs/locale/de";
import { useApi } from "../../hooks/useApi.ts";
import { CoopApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import dayjs from "dayjs";

interface CoopSharesAdminModalProps {
  memberId: string;
  csrfToken: string;
  show: boolean;
  onHide: () => void;
  bestellWizardUrl: string;
}

const CoopSharesAdminModal: React.FC<CoopSharesAdminModalProps> = ({
  memberId,
  csrfToken,
  show,
  onHide,
  bestellWizardUrl,
}) => {
  const coopApi = useApi(CoopApi, csrfToken);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(new Date());
  const [quantity, setQuantity] = useState(1);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    setShowForm(false);
  }, [show]);

  function onAddShares() {
    setLoading(true);

    coopApi
      .coopApiExistingMemberPurchasesSharesCreate({
        existingMemberPurchasesSharesRequestRequest: {
          memberId: memberId,
          numberOfSharesToAdd: quantity,
          asAdmin: true,
          startDate: startDate,
        },
      })
      .then(() => location.reload())
      .catch((error) => {
        setLoading(false);
        handleRequestError(
          error,
          "Fehler bei der manueller Zeichnung der Geno-Anteile",
        );
      });
  }

  function buildTooltip() {
    return (
      <Popover id="popover-basic" style={{ maxWidth: "500px" }}>
        <Popover.Header as="h3">Erklärung</Popover.Header>
        <Popover.Body>
          <p>
            Als Admin kannst du Genossenschaftsanteile manuell hinzufügen und
            hinterlegen, wann der Beitritts- bzw. Zeichnungerklärung durch den
            Vorstand zugestimmt wurde. Relevant ist also der Zeitpunkt, an dem
            die Beitritts- bzw. Zeichnungserklärung durch den Vorstand
            akzeptiert wurde (nicht unbedingt der Zeitpunkt, wann das Mitglied
            diese eingereicht hat).
          </p>
          <p>
            Nutze diese Funktion vor allem dann, wenn du bei bereits bestehenden
            Mitgliedern die Zeichnung von Genossenschaftsanteilen in der
            Vergangenheit eintragen möchtest.
          </p>
          <p>
            Falls das Mitglied gerade aktuell weitere Genossenschaftsanteile
            zeichnen möchte, dann folge diesem{" "}
            <a href={bestellWizardUrl}>Link</a>
          </p>
        </Popover.Body>
      </Popover>
    );
  }

  function buildForm() {
    return (
      <Form>
        <Form.Group id={"start-date"}>
          <Form.Label>Wirksamkeitsdatum</Form.Label>
          <Form.Control
            type={"date"}
            onChange={(event) => setStartDate(new Date(event.target.value))}
            value={dayjs(startDate).format("YYYY-MM-DD")}
          />
        </Form.Group>
        <Form.Group id={"quantity"}>
          <Form.Label>Anzahl</Form.Label>
          <Form.Control
            type={"number"}
            step={1}
            min={1}
            value={quantity}
            onChange={(event) =>
              setQuantity(Number.parseInt(event.target.value))
            }
          />
        </Form.Group>
      </Form>
    );
  }

  function buildChoice() {
    return (
      <div className={"d-flex flex-row gap-2"}>
        <TapirButton
          variant={"outline-primary"}
          text={
            "Zeichnungen von Genossenschaftsanteilen in der Vergangenheit eintragen"
          }
          onClick={() => setShowForm(true)}
        />
        <TapirButton
          variant={"outline-primary"}
          text={
            "Aktuelle Zeichnungen von Genossenschaftsanteilen für das Mitglied hinterlegen"
          }
          onClick={() => location.assign(bestellWizardUrl)}
        />
      </div>
    );
  }

  return (
    <Modal centered={true} show={show} onHide={onHide} size={"lg"}>
      <Modal.Header closeButton={true}>
        <div className={"d-flex gap-2 align-items-center"}>
          <h5 className={"mb-0"}>
            Genossenschaftsanteile als Admin hinzufügen
          </h5>
          <OverlayTrigger
            overlay={buildTooltip()}
            trigger={"click"}
            placement={"bottom"}
          >
            <TapirButton variant={"outline-secondary"} icon={"help"} />
          </OverlayTrigger>
        </div>
      </Modal.Header>
      <Modal.Body>{showForm ? buildForm() : buildChoice()}</Modal.Body>
      {showForm && (
        <Modal.Footer>
          <TapirButton
            text={"Anteile hinzufügen"}
            icon={"save"}
            variant={"primary"}
            onClick={onAddShares}
            loading={loading}
          />
        </Modal.Footer>
      )}
    </Modal>
  );
};

export default CoopSharesAdminModal;
