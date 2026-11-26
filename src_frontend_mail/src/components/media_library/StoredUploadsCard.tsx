import { DocumentDuplicateIcon, TrashIcon } from "@heroicons/react/24/outline";
import { ReactNode, useState } from "react";

import "filepond/dist/filepond.min.css";
import { Badge, Card, Form, Table } from "react-bootstrap";
import { StoredUpload, TapirmailApi } from "tapir-api-client";
import { useAlert } from "../../contexts/alerts";
import { formatDate } from "../../utils/formatDate";
import { getMediaLibraryFileUrl } from "../../utils/getMediaLibraryFileUrl";
import { DEFAULT_PAGE_SIZE } from "../../utils/pagination";
import ConfirmDeleteModal from "../ConfirmDeleteModal";
import TapirButton from "../TapirButton";
import TapirHelpButton from "../TapirHelpButton";
import TapirPagination from "../TapirPagination";

interface StoredUploadsCardProps {
  searchTerm: string;
  onSearchTermChange: (searchTerm: string) => void;
  uploader?: ReactNode;
  storedUploads: StoredUpload[];
  apiClient: TapirmailApi;
  updateStoredUploadsList: () => void;
  itemCount: number;
  currentPage: number;
  goToPage: (pageIndex: number) => void;
}

export default function StoredUploadsCard(props: StoredUploadsCardProps) {
  const showAlert = useAlert();
  const [uploadToDelete, setUploadToDelete] = useState<StoredUpload>();

  function onDeleteConfirmed() {
    if (!uploadToDelete) return;
    props.apiClient
      .storeduploadsDestroy({ uploadId: uploadToDelete.uploadId })
      .then(() => {
        props.updateStoredUploadsList();
      })
      .finally(() => {
        setUploadToDelete(undefined);
      });
  }

  function onCopyUrl(uploadId: string) {
    navigator.clipboard.writeText(getMediaLibraryFileUrl(uploadId));
    showAlert("URL kopiert", "primary");
  }

  function getFilePreview(storedUpload: StoredUpload) {
    const fileName = getDisplayName(storedUpload);
    const fileExtension = fileName.includes(".")
      ? fileName.split(".").pop()!.toLowerCase()
      : undefined;
    if (fileExtension && ["png", "jpg", "jpeg"].includes(fileExtension)) {
      return (
        <a href={getMediaLibraryFileUrl(storedUpload.uploadId)}>
          <img
            src={getMediaLibraryFileUrl(storedUpload.uploadId)}
            style={{ maxHeight: "100px", maxWidth: "100px" }}
            alt="Bildvorschau"
          ></img>
        </a>
      );
    }
    return (
      <Badge bg="secondary">{fileExtension?.toUpperCase() ?? "DATEI"}</Badge>
    );
  }

  return (
    <>
      <Card className="mb-2">
        <Card.Header
          as="h5"
          className="d-flex justify-content-between align-items-center"
        >
          <span>Dateien</span>
          <div className="d-flex gap-2 align-items-center">
            <Form.Control
              type="search"
              size="sm"
              placeholder="Dateiname suchen"
              aria-label="Dateiname suchen"
              value={props.searchTerm}
              onChange={(event) => props.onSearchTermChange(event.target.value)}
              style={{ width: "15rem" }}
            />
            <TapirHelpButton
              title="Dateien hochladen"
              text={
                <div className="text-start">
                  <p>
                    Hochgeladene Dateien werden jetzt sofort gespeichert und
                    sind direkt verwendbar.
                  </p>
                  <p>
                    <strong>Bisher:</strong> Dateien landeten nach dem Hochladen
                    zuerst unter „Noch nicht gespeicherte Dateien“. Erst ein
                    Klick auf „Dateien speichern“ hat sie in die
                    Medienbibliothek übernommen.
                  </p>
                  <p>
                    <strong>Jetzt:</strong> Dateien erscheinen nach dem
                    Hochladen sofort oben in der Liste. Ein Speichern-Schritt
                    ist nicht mehr nötig.
                  </p>
                </div>
              }
            />
          </div>
        </Card.Header>
        <Card.Body>
          {props.uploader}
          <Table striped hover responsive className="align-middle mb-0">
            <thead>
              <tr>
                <th>Vorschau</th>
                <th>Dateiname</th>
                <th></th>
                <th>Gespeichert am</th>
                <th>Hochgeladen von</th>
              </tr>
            </thead>
            <tbody>
              {props.storedUploads.length === 0 && props.searchTerm && (
                <tr>
                  <td colSpan={5} className="text-muted">
                    Keine Dateien gefunden
                  </td>
                </tr>
              )}
              {props.storedUploads.map((storedUpload) => (
                <tr key={storedUpload.uploadId}>
                  <td>{getFilePreview(storedUpload)}</td>
                  <td>
                    <a href={getMediaLibraryFileUrl(storedUpload.uploadId)}>
                      {getDisplayName(storedUpload)}
                    </a>
                  </td>
                  <td>
                    <div className="d-flex gap-2">
                      <TapirButton
                        size="sm"
                        variant="outline-primary"
                        style={{ whiteSpace: "nowrap" }}
                        text="URL kopieren"
                        icon={DocumentDuplicateIcon}
                        onClick={() => onCopyUrl(storedUpload.uploadId)}
                      />
                      <TapirButton
                        size="sm"
                        variant="outline-danger"
                        style={{ whiteSpace: "nowrap" }}
                        text="Löschen"
                        icon={TrashIcon}
                        onClick={() => setUploadToDelete(storedUpload)}
                      />
                    </div>
                  </td>
                  <td className="text-nowrap">
                    {formatDate(storedUpload.stored)}
                  </td>
                  <td>{storedUpload.uploadedBy}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
        {props.itemCount > DEFAULT_PAGE_SIZE && (
          <Card.Footer className="d-flex justify-content-center align-items-center">
            <TapirPagination
              pageSize={DEFAULT_PAGE_SIZE}
              itemCount={props.itemCount}
              currentPage={props.currentPage}
              goToPage={props.goToPage}
            />
          </Card.Footer>
        )}
      </Card>
      <ConfirmDeleteModal
        message={
          <>
            Möchtest du die Datei{" "}
            <strong>{uploadToDelete && getDisplayName(uploadToDelete)}</strong>{" "}
            wirklich löschen? E-Mails, die diese Datei verwenden, können sie
            danach nicht mehr anzeigen.
          </>
        }
        open={!!uploadToDelete}
        onConfirm={onDeleteConfirmed}
        onCancel={() => setUploadToDelete(undefined)}
      />
    </>
  );
}

function getDisplayName(storedUpload: StoredUpload) {
  return storedUpload.fileName.split("/").pop()!;
}
