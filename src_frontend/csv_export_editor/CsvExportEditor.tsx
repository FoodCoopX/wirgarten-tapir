import React, { useEffect, useState } from "react";
import { Card, Col, Dropdown, Row } from "react-bootstrap";
import { v4 as uuidv4 } from "uuid";
import {
  CsvExportModel,
  ExportSegment,
  GenericExportsApi,
  PdfExportTemplate,
} from "../api-client";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import CsvExportBuildModal from "./CsvExportBuildModal.tsx";
import CsvExportModal from "./CsvExportModal.tsx";
import CsvExportTable from "./CsvExportTable.tsx";

interface CsvExportEditorProps {
  csrfToken: string;
}

const CsvExportEditor: React.FC<CsvExportEditorProps> = ({ csrfToken }) => {
  const api = useApi(GenericExportsApi, csrfToken);
  const [segments, setSegments] = useState<ExportSegment[]>([]);
  const [segmentsLoading, setSegmentsLoading] = useState(false);
  const [exports, setExports] = useState<CsvExportModel[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [showCsvExportModal, setShowCsvExportModal] = useState(false);
  const [exportSelectedForDeletion, setExportSelectedForDeletion] =
    useState<CsvExportModel>();
  const [exportSelectedForEdition, setExportSelectedForEdition] =
    useState<CsvExportModel>();
  const [exportSelectedForBuild, setExportSelectedForBuild] =
    useState<CsvExportModel>();
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);
  const [templates, setTemplates] = useState<PdfExportTemplate[]>([]);
  const [creatingFromTemplate, setCreatingFromTemplate] = useState(false);

  useEffect(() => {
    setSegmentsLoading(true);
    Promise.all([
      api.genericExportsExportSegmentsList(),
      api.genericExportsCsvExportTemplatesList(),
    ])
      .then(([segments, templates]) => {
        setSegments(segments);
        setTemplates(templates);
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Segmente",
          setToastDatas,
        ),
      )
      .finally(() => setSegmentsLoading(false));

    loadExports();
  }, []);

  function loadExports() {
    setExportsLoading(true);
    api
      .genericExportsCsvExportsList()
      .then(setExports)
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden der Exports",
          setToastDatas,
        ),
      )
      .finally(() => setExportsLoading(false));
  }

  function deleteExport(exp: CsvExportModel) {
    api
      .genericExportsCsvExportsDestroy({ id: exp.id! })
      .then(() => loadExports())
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Löschen des Exports",
          setToastDatas,
        ),
      )
      .finally(() => setExportSelectedForDeletion(undefined));
  }

  function createExportFromTemplate(templateId: string) {
    setCreatingFromTemplate(true);

    api
      .genericExportsCreateCsvExportFromTemplatesCreate({
        templateId: templateId,
      })
      .then((result) => {
        if (result.orderConfirmed) {
          loadExports();
          return;
        }
        addToast(
          {
            id: uuidv4(),
            variant: "danger",
            message: result.error!,
            title: "Fehler",
          },
          setToastDatas,
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Erzeugen des Exports aus einem Template",
          setToastDatas,
        ),
      )
      .finally(() => setCreatingFromTemplate(false));
  }

  return (
    <>
      <Row className={"mt-4"}>
        <Col>
          <Card>
            <Card.Header>
              <div
                className={
                  "d-flex justify-content-between align-items-center mb-0"
                }
              >
                <h5 className={"mb-0"}>CSV-Export Editor</h5>
                <Dropdown>
                  <Dropdown.Toggle
                    variant="outline-primary"
                    id="dropdown-create"
                    disabled={creatingFromTemplate}
                  >
                    {creatingFromTemplate
                      ? "Wird erzeugt..."
                      : "Neuen Export erzeugen"}
                  </Dropdown.Toggle>
                  <Dropdown.Menu>
                    <Dropdown.Item
                      onClick={() => {
                        setExportSelectedForEdition(undefined);
                        setShowCsvExportModal(true);
                      }}
                      disabled={segmentsLoading}
                    >
                      Leer
                    </Dropdown.Item>
                    <Dropdown.Divider />
                    <Dropdown.Header>Templates</Dropdown.Header>
                    {templates.map((template) => (
                      <Dropdown.Item
                        key={template.id}
                        onClick={() => createExportFromTemplate(template.id)}
                      >
                        {template.name}
                        <br />
                        <small>{template.description}</small>
                      </Dropdown.Item>
                    ))}
                  </Dropdown.Menu>
                </Dropdown>
              </div>
            </Card.Header>
            <Card.Body>
              <CsvExportTable
                exports={exports}
                loading={exportsLoading}
                onExportEdit={(exp) => {
                  setExportSelectedForEdition(exp);
                  setShowCsvExportModal(true);
                }}
                segments={segmentsLoading ? [] : segments}
                onExportDeleteClicked={setExportSelectedForDeletion}
                onExportBuildClicked={setExportSelectedForBuild}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <CsvExportModal
        show={showCsvExportModal}
        onHide={() => setShowCsvExportModal(false)}
        segments={segments}
        loadExports={loadExports}
        csrfToken={csrfToken}
        exportToEdit={exportSelectedForEdition}
        setToastDatas={setToastDatas}
      />
      {exportSelectedForDeletion && (
        <ConfirmDeleteModal
          open={true}
          message={
            'Export "' + exportSelectedForDeletion.name + '" wirklich löschen?'
          }
          onConfirm={() => deleteExport(exportSelectedForDeletion)}
          onCancel={() => setExportSelectedForDeletion(undefined)}
        />
      )}
      {exportSelectedForBuild && (
        <CsvExportBuildModal
          exportToBuild={exportSelectedForBuild}
          show={true}
          csrfToken={csrfToken}
          onHide={() => setExportSelectedForBuild(undefined)}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </>
  );
};

export default CsvExportEditor;
