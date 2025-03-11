import React, { ChangeEvent, useEffect, useState } from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import {
  CsvExportModel,
  ExportSegment,
  ExportSegmentColumn,
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
  const [exportColumns, setExportColumns] = useState<ExportSegmentColumn[]>([]);
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

  function getExportColumns(exp: CsvExportModel) {
    const segment = getSegmentById(exp.exportSegmentId);
    if (!segment) {
      return [];
    }

    return segment.columns.filter((column) =>
      exp.columnIds?.includes(column.id),
    );
  }

  useEffect(() => {
    if (exportToEdit) {
      setExportName(exportToEdit.name);
      setExportSegment(getSegmentById(exportToEdit.exportSegmentId));
      setExportDescription(exportToEdit.description ?? "");
      setExportSeparator(exportToEdit.separator);
      setExportFileName(exportToEdit.fileName);
      setExportEmailRecipients(exportToEdit.emailRecipients ?? []);
      setExportColumns(getExportColumns(exportToEdit));
    } else {
      setExportName("");
      setExportSegment(segments[0]);
      setExportDescription("");
      setExportSeparator(",");
      setExportFileName("");
      setExportEmailRecipients([]);
      setExportColumns([]);
    }
  }, [exportToEdit]);

  function save() {
    if (!exportSegment) return;

    const form = document.getElementById(
      "createCsvExportModalForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setLoading(true);

    const columnIds = exportColumns.map((column) => column.id);
    const request = {
      exportSegmentId: exportSegment.id,
      columnIds: columnIds,
      description: exportDescription,
      name: exportName,
      emailRecipients: exportEmailRecipients,
      fileName: exportFileName,
      separator: exportSeparator,
    };

    let promise;
    if (exportToEdit) {
      promise = api.genericExportsCsvExportsUpdate({
        id: exportToEdit.id,
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

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Neues Export erzeugen</h5>
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

          <Form.Group controlId={"form.emails"}>
            <Form.Label>Empfängers</Form.Label>
            <EmailInput
              onEmailListChange={setExportEmailRecipients}
              addresses={exportEmailRecipients}
            />
          </Form.Group>
          <Form.Group controlId={"form.columns"}>
            <Form.Label>Spalten</Form.Label>
            <ColumnInput
              onSelectedColumnsChange={setExportColumns}
              availableColumns={exportSegment ? exportSegment.columns : []}
              selectedColumns={exportColumns}
            />
          </Form.Group>
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
