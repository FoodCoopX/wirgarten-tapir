import React, { useEffect, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import "dayjs/locale/de";
import { useApi } from "../../hooks/useApi.ts";
import { CoopApi } from "../../api-client";
import TapirButton from "../../components/TapirButton.tsx";
import { handleRequestError } from "../../utils/handleRequestError.ts";
import TapirDateInput from "../../components/TapirDateInput.tsx";
import TapirHelpButton from "../../components/TapirHelpButton.tsx";

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
      <>
        <p>
          Als Admin kannst du Genossenschaftsanteile manuell hinzufügen und
          hinterlegen, wann der Beitritts- bzw. Zeichnungserklärung durch den
          Vorstand zugestimmt wurde.
        </p>
        <p>
          Du kannst zum einen in der Vergangenheit gezeichnete
          Genossenschaftsanteile hinterlegen. Dies ist v.a. relevant wenn ihr
          eure Mitglieder selbstständig anlegen / importieren wollt.
        </p>
        <p>
          Du kannst aber auch für bereits bestehende Mitglieder die Zeichnung
          von Genossenschaftsanteilen eintragen. Dies ist v.a. relevant, wenn
          Mitglieder nicht selbstständig ihren Mitgliederbereich verwalten
          können/wollen. Das Wirksamkeitsdatum der Zeichnung der
          Genossenschaftsanteile ergibt sich hier aus den von euren
          Konfigurationseinstellung abhängigen Regeln und kann nicht durch euch
          festgelegt werden.
        </p>
      </>
    );
  }

  function buildForm() {
    return (
      <Form>
        <Form.Group id={"start-date"}>
          <Form.Label>Wirksamkeitsdatum</Form.Label>
          <TapirDateInput date={startDate} setDate={setStartDate} />
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
          <TapirHelpButton text={buildTooltip()} />
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
