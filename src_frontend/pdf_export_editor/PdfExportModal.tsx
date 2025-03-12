import React, { ChangeEvent, useEffect, useState } from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import {
  AutomatedExportCycleEnum,
  ExportSegment,
  GenericExportsApi,
  PdfExportModel,
} from "../api-client";
import EmailInput from "../components/EmailInput";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";

interface PdfExportModalProps {
  show: boolean;
  onHide: () => void;
  segments: ExportSegment[];
  loadExports: () => void;
  csrfToken: string;
  exportToEdit?: PdfExportModel;
}

const PdfExportModal: React.FC<PdfExportModalProps> = ({
  show,
  onHide,
  segments,
  loadExports,
  csrfToken,
  exportToEdit,
}) => {
  const api = useApi(GenericExportsApi, csrfToken);

  const [exportName, setExportName] = useState("");
  const [exportSegment, setExportSegment] = useState<ExportSegment>();
  const [exportDescription, setExportDescription] = useState("");
  const [exportFileName, setExportFileName] = useState("");
  const [exportEmailRecipients, setExportEmailRecipients] = useState<string[]>(
    [],
  );
  const [exportCycle, setExportCycle] = useState<AutomatedExportCycleEnum>(
    AutomatedExportCycleEnum.Never,
  );
  const [exportDay, setExportDay] = useState(1);
  const [exportHour, setExportHour] = useState("03:00");
  const [exportTemplate, setExportTemplate] = useState("");
  const [exportOneFilePerEntry, setExportOneFilePerEntry] = useState(false);
  const [loading, setLoading] = useState(false);

  function onSegmentSelectChanged(event: ChangeEvent<HTMLSelectElement>) {
    const segmentId = event.target.value;
    for (const segment of segments) {
      if (segment.id === segmentId) {
        setExportSegment(segment);
        return;
      }
    }
    alert("Segment not found " + segmentId);
  }

  useEffect(() => {
    setExportSegment(segments[0]);
  }, [show]);

  function getSegmentById(segmentId: string) {
    for (const segment of segments) {
      if (segment.id === segmentId) return segment;
    }
    alert("Segment not found " + segmentId);
    return undefined;
  }

  useEffect(() => {
    if (exportToEdit) {
      setExportName(exportToEdit.name);
      setExportSegment(getSegmentById(exportToEdit.exportSegmentId));
      setExportDescription(exportToEdit.description ?? "");
      setExportFileName(exportToEdit.fileName);
      setExportEmailRecipients(exportToEdit.emailRecipients ?? []);
      setExportCycle(exportToEdit.automatedExportCycle);
      setExportDay(exportToEdit.automatedExportDay);
      setExportHour(exportToEdit.automatedExportHour);
      setExportTemplate(exportToEdit.template);
      setExportOneFilePerEntry(
        exportToEdit.generateOneFileForEverySegmentEntry,
      );
    } else {
      setExportName("");
      setExportSegment(segments[0]);
      setExportDescription("");
      setExportFileName("");
      setExportEmailRecipients([]);
      setExportCycle(AutomatedExportCycleEnum.Never);
      setExportDay(1);
      setExportHour("00:00");
      setExportTemplate("");
      setExportOneFilePerEntry(false);
    }
  }, [exportToEdit]);

  function save() {
    if (!exportSegment) return;

    const form = document.getElementById(
      "createPdfExportModalForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setLoading(true);

    const request = {
      exportSegmentId: exportSegment.id,
      description: exportDescription,
      name: exportName,
      emailRecipients: exportEmailRecipients,
      fileName: exportFileName,
      template: exportTemplate,
      automatedExportCycle: exportCycle,
      automatedExportDay: exportDay,
      automatedExportHour: exportHour,
      generateOneFileForEverySegmentEntry: exportOneFilePerEntry,
    };

    let promise;
    if (exportToEdit) {
      promise = api.genericExportsPdfExportsUpdate({
        id: exportToEdit.id!,
        pdfExportModelRequest: request,
      });
    } else {
      promise = api.genericExportsPdfExportsCreate({
        pdfExportModelRequest: request,
      });
    }

    promise
      .then(() => {
        loadExports();
        onHide();
      })
      .catch(alert)
      .finally(() => setLoading(false));
  }

  function cycleOptions() {
    return {
      yearly: "Jährlich",
      monthly: "Monatlich",
      weekly: "Wöchentlich",
      daily: "Täglich",
      never: "nie",
    };
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Neues Export erzeugen</h5>
      </Modal.Header>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"createPdfExportModalForm"}
        >
          <Row>
            <Col>
              <Form.Group controlId={"form.name"}>
                <Form.Label>Name</Form.Label>
                <Form.Control
                  type={"text"}
                  placeholder={"Name"}
                  onChange={(event) => setExportName(event.target.value)}
                  required={true}
                  value={exportName}
                />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId={"form.segment"}>
                <Form.Label>Datensegment</Form.Label>
                <Form.Select onChange={onSegmentSelectChanged}>
                  {segments.map((segment) => {
                    return (
                      <option
                        key={segment.id}
                        value={segment.id}
                        selected={
                          exportSegment && segment.id == exportSegment.id
                        }
                      >
                        {segment.displayName}
                      </option>
                    );
                  })}
                </Form.Select>
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Form.Group controlId={"form.description"}>
              <Form.Label>Beschreibung</Form.Label>
              <Form.Control
                type={"text"}
                placeholder={"Beschreibung"}
                as={"textarea"}
                onChange={(event) => setExportDescription(event.target.value)}
                value={exportDescription}
              />
            </Form.Group>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.file name"}>
                <Form.Label>Datei-Name</Form.Label>
                <Form.Control
                  type={"text"}
                  placeholder={"Datei-Name"}
                  onChange={(event) => setExportFileName(event.target.value)}
                  required={true}
                  value={exportFileName}
                />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId={"form.OneFilePerEntry"}>
                <Form.Label>
                  Eine Datei pro Eintrag im Datensegment erzeugen
                </Form.Label>
                <Form.Check
                  onChange={(event) =>
                    setExportOneFilePerEntry(event.target.checked)
                  }
                  required={false}
                  value={exportFileName}
                />
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.emails"}>
                <Form.Label>Empfängers</Form.Label>
                <EmailInput
                  onEmailListChange={setExportEmailRecipients}
                  addresses={exportEmailRecipients}
                />
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.cycle"}>
                <Form.Label>Automatisiertes Export Zyklus</Form.Label>
                <Form.Select
                  onChange={(event) =>
                    setExportCycle(
                      event.target.value as AutomatedExportCycleEnum,
                    )
                  }
                >
                  {Object.entries(cycleOptions()).map(([key, value]) => {
                    return (
                      <option
                        key={key}
                        value={key}
                        selected={exportCycle === key}
                      >
                        {value}
                      </option>
                    );
                  })}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId={"form.day"}>
                <Form.Label>Tag</Form.Label>
                <Form.Control
                  type={"number"}
                  onChange={(event) =>
                    setExportDay(parseInt(event.target.value))
                  }
                  required={true}
                  value={exportDay}
                />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId={"form.hour"}>
                <Form.Label>Uhrzeit</Form.Label>
                <Form.Control
                  type={"time"}
                  onChange={(event) => setExportHour(event.target.value)}
                  required={true}
                  value={exportHour}
                />
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.template"}>
                <Form.Label>Template</Form.Label>
                <Form.Control
                  type={"text"}
                  as={"textarea"}
                  placeholder={"Template"}
                  onChange={(event) => setExportTemplate(event.target.value)}
                  required={true}
                  value={exportTemplate}
                />
              </Form.Group>
            </Col>
          </Row>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={exportToEdit ? "Speichern" : "Erzeugen"}
          icon={"add_circle"}
          variant={"primary"}
          onClick={save}
          loading={loading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default PdfExportModal;
