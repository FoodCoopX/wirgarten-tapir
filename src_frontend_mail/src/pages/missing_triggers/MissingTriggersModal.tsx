import { PlusCircleIcon } from "@heroicons/react/24/outline";
import React, { useState } from "react";
import { Modal } from "react-bootstrap";
import { MissingTrigger, TapirmailApi } from "tapir-api-client";
import { createEmptyMjml } from "../../components/editor";
import TapirButton from "../../components/TapirButton";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";

interface MissingTriggersModalProps {
  open: boolean;
  onHide: () => void;
  missingTriggers: MissingTrigger[];
  reloadData: () => void;
}

const MissingTriggersModal: React.FC<MissingTriggersModalProps> = ({
  open,
  onHide,
  missingTriggers,
  reloadData,
}) => {
  const api = useApi(TapirmailApi);
  const showAlert = useAlert();
  const [loading, setLoading] = useState(false);

  function onCreate(key: string) {
    setLoading(true);

    api
      .tapirmailApiCreateMissingTriggerCreate({
        createMissingTriggerMailRequest: {
          triggerKey: key,
          emptyMjml: createEmptyMjml(),
        },
      })
      .then(reloadData)
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim Erstellen des Mail-Entwurfs", "danger");
      })
      .finally(() => setLoading(false));
  }

  return (
    <Modal show={open} onHide={onHide} size={"lg"} centered={true}>
      <Modal.Header closeButton>
        <Modal.Title>Fehlende Trigger</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>
          Es würden keine veröffentlichte Mail gefunden was folgende Trigger
          einsetzt. Ohne diese Trigger können die betroffene Funktionalitäten
          nicht richtig funktionieren.
        </p>
        <p>
          Hier können sie Mail-Entwürfe erzeugen mit der passende Trigger und
          Standard-Inhalte
        </p>
        <ul>
          {missingTriggers.map((trigger) => (
            <li key={trigger.key}>
              <span className={"d-flex flex-row gap-2 align-items-center"}>
                {trigger.name}
                {
                  <TapirButton
                    variant={"primary"}
                    text={
                      trigger.draftVersionExists
                        ? "Entwurf existiert bereits"
                        : "Erzeugen"
                    }
                    icon={PlusCircleIcon}
                    size={"sm"}
                    onClick={() => onCreate(trigger.key)}
                    disabled={loading || trigger.draftVersionExists}
                  />
                }
              </span>
            </li>
          ))}
        </ul>
      </Modal.Body>
    </Modal>
  );
};

export default MissingTriggersModal;
