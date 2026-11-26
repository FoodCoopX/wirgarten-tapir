import { PlusCircleIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { Badge, Card, Table } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";
import { EmailTemplate, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import Paths from "../../routing";
import { getApiErrorMessage } from "../../utils/apiErrorMessage";
import { formatDate } from "../../utils/formatDate";
import { DEFAULT_PAGE_SIZE } from "../../utils/pagination";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import LabelHelp from "../LabelHelp";
import Loading from "../loading";
import TapirButton from "../TapirButton";
import TapirPagination from "../TapirPagination";
import TapirTooltip from "../TapirTooltip";

const TemplatesCard = () => {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [templateToDelete, setTemplateToDelete] = useState<
    EmailTemplate | undefined
  >();
  const [currentPage, setCurrentPage] = useState(0);
  const [templateCount, setTemplateCount] = useState(0);

  const showAlert = useAlert();
  const navigate = useNavigate();
  const api = useApi(TapirmailApi);

  useEffect(() => {
    if (!api || !showAlert) return;

    api
      .tapirmailApiEmailTemplatePaginatedList({
        limit: DEFAULT_PAGE_SIZE,
        offset: currentPage * DEFAULT_PAGE_SIZE,
      })
      .then((paginatedData) => {
        setTemplates(paginatedData.results ?? []);
        setTemplateCount(paginatedData.count ?? 0);
      })
      .catch(async (err) => {
        console.error(err);
        showAlert(
          await getApiErrorMessage(err, "Fehler beim Laden der Vorlagen"),
          "danger",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [currentPage]);

  function onDeleteTemplateConfirmed() {
    if (!templateToDelete) return;

    api
      .tapirmailApiEmailTemplatePaginatedDestroy({ id: templateToDelete.id! })
      .then(() => {
        showAlert("Vorlage gelöscht: " + templateToDelete.name, "success");
        setTemplates(
          templates.filter((template) => template.id !== templateToDelete.id),
        );
      })
      .catch(async (err) => {
        console.error(err);
        showAlert(
          await getApiErrorMessage(err, "Fehler beim Löschen der Vorlage"),
          "danger",
        );
      })
      .finally(() => {
        setTemplateToDelete(undefined);
      });
  }

  function onDeleteTemplateCancelled() {
    setTemplateToDelete(undefined);
  }

  return (
    <>
      <Card>
        <Card.Header
          as="h5"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Vorlagen</span>
          <Link to={Paths.templateEditorCreate}>
            <TapirButton
              variant="primary"
              text="Neue Vorlage erstellen"
              icon={PlusCircleIcon}
            />
          </Link>
        </Card.Header>
        <Card.Body style={{ padding: 0, border: "none" }}>
          {loading ? (
            <Loading />
          ) : (
            <Table striped hover style={{ margin: "0" }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>
                    Typ
                    <LabelHelp
                      label="Vorlagen-Typ"
                      text={
                        <>
                          <strong>Start-Vorlage:</strong> füllt den
                          E-Mail-Editor vor.
                          <br />
                          <strong>Layout-Vorlage:</strong> Einheitliches
                          Aussehen wie Kopf- und Fußzeile.
                        </>
                      }
                    />
                  </th>
                  <th>Erzeugt am</th>
                  <th>Aktualisiert am</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => (
                  <tr
                    key={template.id}
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(
                        Paths.templateEditorEdit.replace(
                          ":templateId",
                          template.id!!,
                        ),
                      )
                    }
                  >
                    <td>{template.name}</td>
                    <td>
                      {template.templateType === "layout"
                        ? "Layout-Vorlage"
                        : "Start-Vorlage"}
                      {template.isDefaultLayout && (
                        <>
                          {" "}
                          <TapirTooltip
                            id={`default-layout-${template.id}`}
                            text="Neue E-Mails nutzen dieses Layout automatisch."
                          >
                            <Badge bg="primary">Standard</Badge>
                          </TapirTooltip>
                        </>
                      )}
                    </td>
                    <td>{formatDate(template.createdAt)}</td>
                    <td>{formatDate(template.updatedAt)}</td>
                    <td
                      style={{
                        alignContent: "right",
                      }}
                    >
                      <TapirButton
                        variant={"outline-danger"}
                        size={"sm"}
                        icon={TrashIcon}
                        onClick={(event) => {
                          event.stopPropagation();
                          setTemplateToDelete(template);
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
        {templateCount > DEFAULT_PAGE_SIZE && (
          <Card.Footer className="d-flex justify-content-center align-items-center">
            <TapirPagination
              pageSize={DEFAULT_PAGE_SIZE}
              itemCount={templateCount}
              currentPage={currentPage}
              goToPage={setCurrentPage}
            />
          </Card.Footer>
        )}
      </Card>
      <ConfirmDeleteModal
        message={
          <>
            Möchtest du die Vorlage <strong>{templateToDelete?.name}</strong>{" "}
            wirklich löschen?
          </>
        }
        open={!!templateToDelete}
        onConfirm={onDeleteTemplateConfirmed}
        onCancel={onDeleteTemplateCancelled}
      />
    </>
  );
};

export default TemplatesCard;
