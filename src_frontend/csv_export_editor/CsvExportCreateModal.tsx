import React, { ChangeEvent, useEffect, useState } from "react";
import { Col, Form, Modal, Row } from "react-bootstrap";
import {
  ExportSegment,
  ExportSegmentColumn,
  GenericExportsApi,
} from "../api-client";
import EmailInput from "../components/EmailInput";
import ColumnInput from "./ColumnInput.tsx";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";

interface CsvExportCreateModalProps {
  show: boolean;
  onHide: () => void;
  segments: ExportSegment[];
  loadExports: () => void;
  csrfToken: string;
}

const CsvExportCreateModal: React.FC<CsvExportCreateModalProps> = ({
  show,
  onHide,
  segments,
  loadExports,
  csrfToken,
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
  const [createLoading, setCreateLoading] = useState(false);
  const [formValidated, setFormValidated] = useState(false);

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

  function createExport() {
    if (!exportSegment) return;

    const form = document.getElementById(
      "createCsvExportModalForm",
    ) as HTMLFormElement;
    if (!form.reportValidity()) return;

    setCreateLoading(true);

    const columnIds = exportColumns.map((column) => column.id);
    api
      .genericExportsCsvExportsCreate({
        csvExportModelRequest: {
          exportSegmentId: exportSegment.id,
          columnIds: columnIds,
          description: exportDescription,
          name: exportName,
          emailRecipients: exportEmailRecipients,
          fileName: exportFileName,
          separator: exportSeparator,
        },
      })
      .then(() => {
        loadExports();
        onHide();
      })
      .catch(alert)
      .finally(() => setCreateLoading(false));
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
          validated={formValidated}
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
                />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId={"form.segment"}>
                <Form.Label>Datensegment</Form.Label>
                <Form.Select onChange={onSegmentSelectChanged}>
                  {segments.map((segment) => {
                    return (
                      <option key={segment.id} value={segment.id}>
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
          text={"Erzeugen"}
          icon={"add_circle"}
          variant={"primary"}
          onClick={createExport}
          loading={createLoading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default CsvExportCreateModal;
