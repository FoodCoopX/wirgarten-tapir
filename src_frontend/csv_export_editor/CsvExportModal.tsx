import React, { ChangeEvent, useEffect, useState } from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import {
  AutomatedExportCycleEnum,
  CsvExportModel,
  ExportSegment,
  GenericExportsApi,
} from "../api-client";
import EmailInput from "../components/EmailInput";
import ColumnInput from "./ColumnInput.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";

interface CsvExportModalProps {
  show: boolean;
  onHide: () => void;
  segments: ExportSegment[];
  loadExports: () => void;
  csrfToken: string;
  exportToEdit?: CsvExportModel;
}

const CsvExportModal: React.FC<CsvExportModalProps> = ({
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
  const [exportSeparator, setExportSeparator] = useState("");
  const [exportFileName, setExportFileName] = useState("");
  const [exportEmailRecipients, setExportEmailRecipients] = useState<string[]>(
    [],
  );
  const [exportColumnIds, setExportColumnIds] = useState<string[]>([]);
  const [exportColumnsNames, setExportColumnsNames] = useState<string[]>([]);
  const [exportCycle, setExportCycle] = useState<AutomatedExportCycleEnum>(
    AutomatedExportCycleEnum.Never,
  );
  const [exportDay, setExportDay] = useState(1);
  const [exportHour, setExportHour] = useState("03:00");
  const [loading, setLoading] = useState(false);

  function onSegmentSelectChanged(event: ChangeEvent<HTMLSelectElement>) {
    const segmentId = event.target.value;
    if (exportSegment && segmentId === exportSegment.id) return;

    for (const segment of segments) {
      if (segment.id === segmentId) {
        if (!allColumnsEqual(segment)) {
          setExportColumnIds([]);
          setExportColumnsNames([]);
        }
        setExportSegment(segment);
        return;
      }
    }
    alert("Segment not found " + segmentId);
  }

  function allColumnsEqual(newSegment: ExportSegment) {
    if (!exportSegment) return false;

    for (const newColumn of newSegment.columns) {
      let found = false;
      for (const oldColumn of exportSegment.columns) {
        if (newColumn.id === oldColumn.id) {
          found = true;
          break;
        }
      }
      if (!found) {
        return false;
      }
    }

    return true;
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
      setExportSeparator(exportToEdit.separator);
      setExportFileName(exportToEdit.fileName);
      setExportEmailRecipients(exportToEdit.emailRecipients ?? []);
      setExportColumnIds(exportToEdit.columnIds ?? []);
      setExportColumnsNames(exportToEdit.customColumnNames ?? []);
      setExportCycle(exportToEdit.automatedExportCycle);
      setExportDay(exportToEdit.automatedExportDay);
      setExportHour(exportToEdit.automatedExportHour);
    } else {
      setExportName("");
      setExportSegment(segments[0]);
      setExportDescription("");
      setExportSeparator(",");
      setExportFileName("");
      setExportEmailRecipients([]);
      setExportColumnIds([]);
      setExportColumnsNames([]);
      setExportCycle(AutomatedExportCycleEnum.Never);
      setExportDay(1);
      setExportHour("00:00");
    }
  }, [exportToEdit]);

  function save() {
    if (!exportSegment) return;

    const form = document.getElementById(
      "createCsvExportModalForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setLoading(true);

    const request = {
      exportSegmentId: exportSegment.id,
      columnIds: exportColumnIds,
      customColumnNames: exportColumnsNames,
      description: exportDescription,
      name: exportName,
      emailRecipients: exportEmailRecipients,
      fileName: exportFileName,
      separator: exportSeparator,
      automatedExportCycle: exportCycle,
      automatedExportDay: exportDay,
      automatedExportHour: exportHour,
    };

    let promise;
    if (exportToEdit) {
      promise = api.genericExportsCsvExportsUpdate({
        id: exportToEdit.id!,
        csvExportModelRequest: request,
      });
    } else {
      promise = api.genericExportsCsvExportsCreate({
        csvExportModelRequest: request,
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

  function onSeparatorChanged(event: ChangeEvent<HTMLInputElement>) {
    event.target.value = event.target.value.slice(0, 1);
    setExportSeparator(event.target.value);
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
    <Modal show={show} onHide={onHide} centered={true} size={"lg"}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Neuen Export erzeugen</h5>
      </Modal.Header>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"createCsvExportModalForm"}
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
              <Form.Group controlId={"form.separator"}>
                <Form.Label>Trennzeichen</Form.Label>
                <Form.Control
                  type={"text"}
                  placeholder={"Trennzeichen"}
                  onChange={onSeparatorChanged}
                  required={true}
                  value={exportSeparator}
                />
                <Form.Text>Nur ein Zeichen</Form.Text>
              </Form.Group>
            </Col>
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
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.emails"}>
                <Form.Label>Empfänger</Form.Label>
                <EmailInput
                  onEmailListChange={setExportEmailRecipients}
                  addresses={exportEmailRecipients}
                />
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.columns"}>
                <Form.Label>Spalten</Form.Label>
                <ColumnInput
                  onSelectedColumnsChange={(columns, columnNames) => {
                    setExportColumnIds(columns);
                    setExportColumnsNames(columnNames);
                  }}
                  availableColumns={exportSegment ? exportSegment.columns : []}
                  selectedColumnIds={exportColumnIds}
                  columnNames={exportColumnsNames}
                />
              </Form.Group>
            </Col>
          </Row>
          <Row>
            <Col>
              <Form.Group controlId={"form.cycle"}>
                <Form.Label>Automatisierter Export-Zyklus</Form.Label>
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

export default CsvExportModal;
