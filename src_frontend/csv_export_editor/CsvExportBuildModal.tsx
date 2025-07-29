import React, { useState } from "react";
import { Form, Modal } from "react-bootstrap";
import {
  BuildCsvExportResponse,
  CsvExportModel,
  GenericExportsApi,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import dayjs from "dayjs";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { ToastData } from "../types/ToastData.ts";

interface CsvExportBuildModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  exportToBuild: CsvExportModel;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const CsvExportBuildModal: React.FC<CsvExportBuildModalProps> = ({
  show,
  onHide,
  csrfToken,
  exportToBuild,
  setToastDatas,
}) => {
  const api = useApi(GenericExportsApi, csrfToken);

  const [datetime, setDatetime] = useState(new Date());
  const [loading, setLoading] = useState(false);

  function buildExport() {
    setLoading(true);
    api
      .genericExportsBuildCsvExportRetrieve({
        csvExportId: exportToBuild.id,
        referenceDatetime: datetime,
      })
      .then(downloadExportFile)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Bauen des Exports: " + error.message,
          setToastDatas,
        ),
      )
      .finally(() => {
        setLoading(false);
        onHide();
      });
  }

  function downloadExportFile(response: BuildCsvExportResponse) {
    const element = document.createElement("a");
    element.setAttribute(
      "href",
      "data:text/plain;charset=utf-8," +
        encodeURIComponent(response.fileAsString),
    );
    element.setAttribute("download", response.fileName);

    element.style.display = "none";
    element.click();
  }

  return (
    <Modal show={show} onHide={onHide} centered={true}>
      <Modal.Header closeButton>
        <h5 className={"mb-0"}>Export erstellen: {exportToBuild.name}</h5>
      </Modal.Header>
      <Modal.Body>
        <Form
          className={"d-flex flex-column gap-2"}
          id={"createCsvExportBuildModalForm"}
        >
          <Form.Group controlId={"form.name"}>
            <Form.Label>Datum</Form.Label>
            <Form.Control
              type={"datetime-local"}
              onChange={(event) => {
                setDatetime(new Date(event.target.value));
              }}
              required={true}
              value={dayjs(datetime).format("YYYY-MM-DDTHH:mm")}
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

export default CsvExportBuildModal;
