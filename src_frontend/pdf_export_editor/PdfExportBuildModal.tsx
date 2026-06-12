import dayjs from "dayjs";
import React, { useRef, useState } from "react";
import { Form, Modal } from "react-bootstrap";
import { GenericExportsApi, PdfExportModel } from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import TapirHelpButton from "../components/TapirHelpButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface PdfExportBuildModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  exportToBuild: PdfExportModel;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

function downloadExportFile(url: string) {
  const element = document.createElement("a");
  element.setAttribute("href", url);

  element.style.display = "none";
  element.click();
}

const PdfExportBuildModal: React.FC<PdfExportBuildModalProps> = ({
  show,
  onHide,
  csrfToken,
  exportToBuild,
  setToastDatas,
}) => {
  const api = useApi(GenericExportsApi, csrfToken);

  const [datetime, setDatetime] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  function buildExport() {
    if (!formRef.current) {
      return;
    }

    if (!formRef.current.reportValidity()) {
      return;
    }

    setLoading(true);
    api
      .genericExportsBuildPdfExportRetrieve({
        pdfExportId: exportToBuild.id,
        referenceDatetime: datetime,
      })
      .then(downloadExportFile)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Bauen des Exports",
          setToastDatas,
        ),
      )
      .finally(() => {
        setLoading(false);
        onHide();
      });
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Export erstellen: {exportToBuild.name}</h5>
      </Modal.Header>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"createPdfExportBuildModalForm"}
          ref={formRef}
        >
          <Form.Group controlId={"form.name"}>
            <Form.Label>Datum</Form.Label>
            <div className={"d-flex flex-row gap-2"}>
              <Form.Control
                type={"datetime-local"}
                onChange={(event) => setDatetime(new Date(event.target.value))}
                required={true}
                value={dayjs(datetime).format("YYYY-MM-DDTHH:mm")}
              />
              <TapirHelpButton text={"WIP"} />
            </div>
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
