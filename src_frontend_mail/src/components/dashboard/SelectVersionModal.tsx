import {
  ArchiveBoxArrowDownIcon,
  DocumentDuplicateIcon,
  PaperAirplaneIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { ButtonGroup, Dropdown, DropdownButton, Modal } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import {
  EmailConfiguration,
  EmailConfigurationVersion,
  TapirmailApi,
} from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { useApi } from "../../hooks/useApi";
import Paths from "../../routing";
import { getDisplayName } from "../../utils/emailConfigurationVersionDisplayName";
import { mjmlToHtml } from "../../utils/mjml";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import ConfirmModal from "../ConfirmModal";
import TapirButton from "../TapirButton";
import TapirTooltip from "../TapirTooltip";
import EmailConfigurationVersionSelect from "../emailConfigurationVersionSelect";
import SendTestMailModal from "./SendTestMailModal";

const SelectVersionModal = ({
  emailConfiguration,
  open,
  onClose,
  onDataChanged,
  selectedVersionOnOpen,
}: {
  emailConfiguration: EmailConfiguration;
  open: boolean;
  onClose: () => void;
  onDataChanged: () => void;
  selectedVersionOnOpen?: string;
}) => {
  const configApi = useApi(TapirmailApi);
  const versionApi = useApi(TapirmailApi);
  const showAlert = useAlert();
  const navigate = useNavigate();

  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [versions, setVersions] = useState<EmailConfigurationVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [htmlContent, setHtmlContent] = useState<string>("");
  const [duplicateLoading, setDuplicateLoading] = useState(false);

  const [confirmArchiveVersionModalOpen, setConfirmArchiveVersionModalOpen] =
    useState(false);
  const [confirmDeleteVersionModalOpen, setConfirmDeleteVersionModalOpen] =
    useState(false);
  const [confirmDeleteEmailModalOpen, setConfirmDeleteEmailModalOpen] =
    useState(false);

  const onDeleteEmailConfigConfirmed = () => {
    if (!emailConfiguration) return;

    configApi
      .tapirmailApiEmailConfigurationDestroy({ id: emailConfiguration.id! })
      .then(() => {
        showAlert("E-Mail gelöscht: " + emailConfiguration.name, "success");
        onClose();
        onDataChanged();
      })
      .catch((err) => {
        console.error(err);
        showAlert("Fehler beim Löschen der E-Mail", "danger");
      })
      .finally(() => {
        setConfirmDeleteEmailModalOpen(false);
      });
  };

  const selectedVersion = versions.find((v) => v.id === selectedVersionId);

  useEffect(() => {
    if (!selectedVersion) return;
    setHtmlContent(mjmlToHtml(selectedVersion.content ?? ""));
  }, [selectedVersion]);

  const fetchVersions = () =>
    configApi
      .tapirmailApiEmailConfigurationVersionsList({
        id: emailConfiguration.id!,
        limit: 100,
      })
      .then((data) => {
        const versions = data.results ?? [];
        versions.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
        setVersions(versions);
        setSelectedVersionId(selectedVersionOnOpen ?? versions[0].id!);
      })
      .catch((err) => {
        console.error(err);
        showAlert("Beim Laden ist ein Fehler aufgetreten.", "danger");
      });

  useEffect(() => {
    if (!emailConfiguration || !configApi) return;

    fetchVersions();
  }, [emailConfiguration]);

  const handleCloseSendModal = () => setSendModalOpen(false);
  const handleEdit = () => {
    onClose();
    navigate(Paths.emailConfigurationEdit.replace(":id", selectedVersionId));
  };
  const handleArchive = () => {
    if (!selectedVersionId || !selectedVersion) return;

    versionApi
      .tapirmailApiEmailConfigurationVersionArchiveCreate({
        id: selectedVersionId,
      })
      .then(() => {
        showAlert(
          "Version archiviert: " + getDisplayName(selectedVersion),
          "success",
        );
        fetchVersions();
        onDataChanged();
      })
      .catch((error) => {
        console.error(error);
        showAlert(
          "Fehler beim Archivieren von " + getDisplayName(selectedVersion),
          "danger",
        );
      })
      .finally(() => {
        setConfirmArchiveVersionModalOpen(false);
      });
  };
  const handleDelete = () => {
    if (!selectedVersionId || !selectedVersion) return;

    versionApi
      .tapirmailApiEmailConfigurationVersionDestroy({ id: selectedVersionId })
      .then(() => {
        showAlert(
          "Version gelöscht: " + getDisplayName(selectedVersion),
          "success",
        );
        fetchVersions();
      })
      .catch((error) => {
        console.error(error);
        showAlert(
          "Fehler beim Löschen von " + getDisplayName(selectedVersion),
          "danger",
        );
      })
      .finally(() => {
        setConfirmDeleteVersionModalOpen(false);
      });
  };

  const onDuplicateClicked = () => {
    setDuplicateLoading(true);

    configApi
      .tapirmailApiEmailConfigurationDuplicateRetrieve({
        id: emailConfiguration.id!,
      })
      .then(() => {
        showAlert("Kopie erstellt", "success");
        onClose();
        onDataChanged();
      })
      .catch((error) => {
        console.error(error);
        showAlert("Fehler beim erstellen der Kopie", "danger");
      })
      .finally(() => {
        setDuplicateLoading(false);
      });
  };

  const archiveButtonDisabled =
    !selectedVersion || selectedVersion?.status !== "released";
  const deleteDropdownDisabled =
    !selectedVersion ||
    (!selectedVersion?.canBeDeleted && !emailConfiguration?.canBeDeleted);
  return (
    <>
      <Modal
        show={
          Boolean(open) &&
          !sendModalOpen &&
          !confirmArchiveVersionModalOpen &&
          !confirmDeleteVersionModalOpen &&
          !confirmDeleteEmailModalOpen
        }
        onHide={onClose}
        dialogClassName="preview-modal"
        centered={true}
      >
        <Modal.Header closeButton>
          <Modal.Title>
            Email Konfiguration: {emailConfiguration?.name}
          </Modal.Title>
        </Modal.Header>
        {emailConfiguration && (
          <Modal.Body>
            <div style={{ marginBottom: "0.5em", fontWeight: "bold" }}>
              Welche Version möchtest du editieren?
            </div>
            <div className="d-flex justify-content-between">
              <div style={{ width: "100%", paddingRight: "10em" }}>
                <EmailConfigurationVersionSelect
                  versions={versions}
                  selectedVersionId={selectedVersionId}
                  onChange={(id: string) => setSelectedVersionId(id)}
                />
              </div>
              <div className="d-flex gap-2">
                <TapirTooltip
                  id={"archive-button"}
                  text={
                    archiveButtonDisabled && selectedVersion
                      ? "Nur veröffentlichte Versionen können archiviert werden."
                      : "Archivieren"
                  }
                >
                  <TapirButton
                    variant={
                      archiveButtonDisabled
                        ? "outline-secondary"
                        : "outline-danger"
                    }
                    icon={ArchiveBoxArrowDownIcon}
                    disabled={archiveButtonDisabled}
                    onClick={() => setConfirmArchiveVersionModalOpen(true)}
                  />
                </TapirTooltip>

                <TapirTooltip
                  id={"delete-button"}
                  text={
                    selectedVersion && !selectedVersion?.canBeDeleted
                      ? "Diese Version kann nicht gelöscht werden, da sie bereits verschickt wurde."
                      : "Löschen"
                  }
                >
                  {versions.length > 1 &&
                  selectedVersion?.canBeDeleted &&
                  emailConfiguration?.canBeDeleted ? (
                    <DropdownButton
                      disabled={deleteDropdownDisabled}
                      as={ButtonGroup}
                      variant={
                        deleteDropdownDisabled
                          ? "outline-secondary"
                          : "outline-danger"
                      }
                      style={{ height: "100%" }}
                      title={<TrashIcon width="1.5em" />}
                      id="bg-nested-dropdown"
                    >
                      <TapirTooltip
                        id={"delete-button"}
                        text={
                          "Diese Version kann nicht gelöscht werden, da sie bereits verschickt wurde."
                        }
                        enabled={!selectedVersion?.canBeDeleted}
                      >
                        <Dropdown.Item
                          disabled={!selectedVersion?.canBeDeleted}
                          onClick={() => setConfirmDeleteVersionModalOpen(true)}
                          eventKey="1"
                        >
                          Diese Version löschen
                        </Dropdown.Item>
                      </TapirTooltip>

                      <TapirTooltip
                        id={"delete-button-config" + emailConfiguration.id}
                        text={
                          "Diese E-Mail kann nicht gelöscht werden, da sie bereits verschickt wurde."
                        }
                        enabled={!emailConfiguration?.canBeDeleted}
                      >
                        <Dropdown.Item
                          disabled={!emailConfiguration?.canBeDeleted}
                          onClick={() => setConfirmDeleteEmailModalOpen(true)}
                          eventKey="2"
                        >
                          Alle Versionen löschen
                        </Dropdown.Item>
                      </TapirTooltip>
                    </DropdownButton>
                  ) : (
                    <TapirButton
                      variant={
                        deleteDropdownDisabled
                          ? "outline-secondary"
                          : "outline-danger"
                      }
                      icon={TrashIcon}
                      disabled={deleteDropdownDisabled}
                      onClick={() => setConfirmDeleteEmailModalOpen(true)}
                    />
                  )}
                </TapirTooltip>
              </div>
            </div>
            <hr />
            <div style={{ marginBottom: "0.5em" }}>
              <strong>Betreff:</strong>&nbsp;{selectedVersion?.subject}
            </div>
            {selectedVersion?.content && (
              <iframe
                title="E-Mail-Vorschau"
                srcDoc={htmlContent}
                style={{
                  width: "100%",
                  height: "60vh",
                  border: "1px solid black",
                }}
              />
            )}
          </Modal.Body>
        )}
        <Modal.Footer
          style={{ display: "flex", justifyContent: "space-between" }}
        >
          <div className="d-flex gap-2">
            <TapirButton
              variant="secondary"
              text="Abbrechen"
              icon={XMarkIcon}
              onClick={onClose}
            />
            <TapirButton
              variant="primary"
              text="Kopie erstellen"
              icon={DocumentDuplicateIcon}
              onClick={onDuplicateClicked}
              disabled={duplicateLoading}
            />
          </div>
          <div className="d-flex gap-2">
            <TapirButton
              variant="outline-primary"
              text="Testmail senden"
              icon={PaperAirplaneIcon}
              onClick={() => setSendModalOpen(true)}
              disabled={!selectedVersion || false}
            />
            <TapirButton
              variant="primary"
              text="Editieren"
              icon={PencilIcon}
              onClick={handleEdit}
              disabled={!selectedVersion || false}
            />
          </div>
        </Modal.Footer>
      </Modal>
      <SendTestMailModal
        open={sendModalOpen}
        emailConfigurationVersion={selectedVersion!}
        onClose={handleCloseSendModal}
      />
      <ConfirmModal
        message={
          <>
            Möchtest du wirklich die Version '
            <strong>{getDisplayName(selectedVersion)}</strong>' der Email{" "}
            <strong>{emailConfiguration?.name}</strong> archivieren?
          </>
        }
        open={confirmArchiveVersionModalOpen}
        onConfirm={handleArchive}
        onCancel={() => setConfirmArchiveVersionModalOpen(false)}
        confirmButtonIcon={ArchiveBoxArrowDownIcon}
        confirmButtonText={"Archivieren"}
        title={"Archivieren bestätigen"}
        confirmButtonVariant="danger"
      />
      <ConfirmDeleteModal
        message={
          <>
            Möchtest du wirklich die Version '
            <strong>{getDisplayName(selectedVersion)}</strong>' der Email{" "}
            <strong>{emailConfiguration?.name}</strong> löschen?
          </>
        }
        open={confirmDeleteVersionModalOpen}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDeleteVersionModalOpen(false)}
      />

      <ConfirmDeleteModal
        message={
          <>
            Möchtest du wirklich die E-Mail{" "}
            <strong>{emailConfiguration?.name}</strong> löschen? Alle damit
            verbundenen Versionen und Versand werden ebenfalls gelöscht.
          </>
        }
        open={confirmDeleteEmailModalOpen}
        onConfirm={onDeleteEmailConfigConfirmed}
        onCancel={() => {
          setConfirmDeleteEmailModalOpen(false);
        }}
      />
    </>
  );
};

export default SelectVersionModal;
