import React, { useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { GenericExportsApi, PdfExportModel } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";

interface PdfExportBuildModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  exportToBuild: PdfExportModel;
}

const PdfExportBuildModal: React.FC<PdfExportBuildModalProps> = ({
  show,
  onHide,
  csrfToken,
  exportToBuild,
}) => {
  const api = useApi(GenericExportsApi, csrfToken);

  const [datetime, setDatetime] = useState(new Date());
  const [loading, setLoading] = useState(false);

  function buildExport() {
    setLoading(true);
    api
      .genericExportsBuildPdfExportRetrieve({
        pdfExportId: exportToBuild.id,
        referenceDatetime: datetime,
      })
      .then(downloadExportFile)
      .catch(alert)
      .finally(() => {
        setLoading(false);
        onHide();
      });
  }

  function downloadExportFile(url: string) {
    const element = document.createElement("a");
    element.setAttribute("href", url);

    element.style.display = "none";
    element.click();
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Export bauen: {exportToBuild.name}</h5>
      </Modal.Header>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"createPdfExportBuildModalForm"}
        >
          <Form.Group controlId={"form.name"}>
            <Form.Label>Datum</Form.Label>
            <Form.Control
              type={"datetime-local"}
              onChange={(event) => setDatetime(new Date(event.target.value))}
              required={true}
            />
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <TapirButton
          text={"Exportieren"}
          icon={"attach_file"}
          variant={"primary"}
          onClick={buildExport}
          loading={loading}
        />
      </Modal.Footer>
    </Modal>
  );
};

export default PdfExportBuildModal;
