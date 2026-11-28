import React, { useEffect, useRef } from "react";
import { Button, Form, Row } from "react-bootstrap";
import { ModeEnum, SegmentOption } from "tapir-api-client";
import { getModeDisplay } from "../../utils/getModeDisplay";

interface MailCategoryFormProps {
  open: boolean;
  categoryName: string;
  setCategoryName: (name: string) => void;
  categoryMode: ModeEnum;
  setCategoryMode: (mode: ModeEnum) => void;
  segmentName: string;
  setSegmentName: (name: string) => void;
  externalsEnabled: boolean;
  setExternalsEnabled: (enabled: boolean) => void;
  segmentOptions: SegmentOption[];
  onOpenSegmentPicker: () => void;
}

const MailCategoryForm: React.FC<MailCategoryFormProps> = ({
  open,
  categoryName,
  setCategoryName,
  categoryMode,
  setCategoryMode,
  segmentName,
  setSegmentName,
  externalsEnabled,
  setExternalsEnabled,
  segmentOptions,
  onOpenSegmentPicker,
}) => {
  const nameRef = useRef<HTMLInputElement | null>(null);
  const selectedSegment = segmentOptions.find(
    (option) => option.id === segmentName,
  );

  useEffect(() => {
    if (open) {
      nameRef.current?.focus();
    }
  }, [open]);

  return (
    <Form>
      <Row>
        <Form.Group>
          <Form.Label>Name</Form.Label>
          <Form.Control
            ref={nameRef}
            required={true}
            className={categoryName ? "" : "is-invalid"}
            type="text"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
          />
        </Form.Group>
      </Row>
      <Row className={"mt-2"}>
        <Form.Group>
          <Form.Label>Modus</Form.Label>
          <Form.Select
            value={categoryMode}
            onChange={(event) =>
              setCategoryMode(event.target.value as ModeEnum)
            }
          >
            {Object.values(ModeEnum).map((mode) => (
              <option key={mode} value={mode}>
                {getModeDisplay(mode, true)}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
      </Row>
      <Row className={"mt-2"}>
        <Form.Group>
          <Form.Label>Segment</Form.Label>
          <div className="d-flex align-items-center gap-2">
            <div className="flex-grow-1">
              {segmentName ? (
                <>
                  <div>{selectedSegment?.label ?? segmentName}</div>
                  {selectedSegment?.description && (
                    <small className="text-muted">
                      {selectedSegment.description}
                    </small>
                  )}
                </>
              ) : (
                <span className="text-muted">Kein Segment</span>
              )}
            </div>
            <Button
              variant="outline-primary"
              size="sm"
              onClick={onOpenSegmentPicker}
            >
              {segmentName ? "Ändern" : "Auswählen"}
            </Button>
            {segmentName && (
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setSegmentName("")}
              >
                Entfernen
              </Button>
            )}
          </div>
        </Form.Group>
      </Row>
      <Row className={"mt-4"}>
        <Form.Group controlId={"externals"}>
          <Form.Check
            checked={externalsEnabled}
            onChange={(event) => setExternalsEnabled(event.target.checked)}
            label={"Können Nicht-Mitglieder sich für diese Kategorie anmelden?"}
          />
        </Form.Group>
      </Row>
    </Form>
  );
};

export default MailCategoryForm;
