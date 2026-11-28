import * as FilePondJs from "filepond";
import {
  FilePondErrorDescription,
  FilePondFile,
  registerPlugin,
} from "filepond";
import { useEffect, useRef, useState } from "react";
import { FilePond } from "react-filepond";

import FilePondPluginImageExifOrientation from "filepond-plugin-image-exif-orientation";
import FilePondPluginImagePreview from "filepond-plugin-image-preview";
import "filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css";
import "filepond/dist/filepond.min.css";
import { Button } from "react-bootstrap";
import { Link } from "react-router-dom";
import { StoredUpload, TapirmailApi } from "tapir-api-client";
import StoredUploadsCard from "../components/media_library/StoredUploadsCard";
import { useAlert } from "../contexts/alerts";
import env from "../env";
import { useApi } from "../hooks/useApi";
import { DEFAULT_PAGE_SIZE } from "../utils/pagination";
import { addCsrfToken } from "../utils/requests";

registerPlugin(FilePondPluginImageExifOrientation, FilePondPluginImagePreview);

export default function MediaLibrary() {
  const [storedUploads, setStoredUploads] = useState<StoredUpload[]>([]);
  const [storedUploadsPage, setStoredUploadsPage] = useState(0);
  const [storedUploadsCount, setStoredUploadsCount] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [reloadCounter, setReloadCounter] = useState(0);

  const apiClient = useApi(TapirmailApi);
  const showAlert = useAlert();
  const pond = useRef<FilePond>(null);

  function onFilePondInit() {
    FilePondJs.setOptions({
      server: {
        url: (env.REACT_APP_API_ROOT as string) + "/api/media_library/filepond",
        process: {
          url: "/process/",
          method: "POST",
          ondata: addCsrfToken,
        },
        revert: "/revert/",
        restore: "/restore/",
        load: "/load/?target=",
        fetch: "/fetch/?target=",
      },
      labelIdle:
        'Dateien hierher ziehen oder <span class="filepond--label-action">durchsuchen</span>',
      labelInvalidField: "Das Feld enthält ungültige Dateien",
      labelFileWaitingForSize: "Dateigröße wird ermittelt",
      labelFileSizeNotAvailable: "Dateigröße nicht verfügbar",
      labelFileLoading: "Wird geladen",
      labelFileLoadError: "Fehler beim Laden",
      labelFileProcessing: "Wird hochgeladen",
      labelFileProcessingComplete: "Hochgeladen",
      labelFileProcessingAborted: "Hochladen abgebrochen",
      labelFileProcessingError: "Fehler beim Hochladen",
      labelFileProcessingRevertError: "Fehler beim Zurücksetzen",
      labelFileRemoveError: "Fehler beim Entfernen",
      labelTapToCancel: "Klicken zum Abbrechen",
      labelTapToRetry: "Klicken zum Wiederholen",
      labelTapToUndo: "Klicken zum Rückgängigmachen",
      labelButtonRemoveItem: "Entfernen",
      labelButtonAbortItemLoad: "Abbrechen",
      labelButtonRetryItemLoad: "Wiederholen",
      labelButtonAbortItemProcessing: "Abbrechen",
      labelButtonUndoItemProcessing: "Rückgängig",
      labelButtonRetryItemProcessing: "Wiederholen",
      labelButtonProcessItem: "Hochladen",
    });
  }

  function updateStoredUploadsList() {
    apiClient
      .storeduploadsList({
        limit: DEFAULT_PAGE_SIZE,
        offset: storedUploadsPage * DEFAULT_PAGE_SIZE,
        search: search || undefined,
      })
      .then((result) => {
        if (result.results.length === 0 && storedUploadsPage > 0) {
          setStoredUploadsPage(storedUploadsPage - 1);
          return;
        }
        setStoredUploads(result.results);
        setStoredUploadsCount(result.count);
      });
  }

  useEffect(updateStoredUploadsList, [
    storedUploadsPage,
    search,
    reloadCounter,
  ]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput);
      setStoredUploadsPage(0);
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  function onFileUploaded(
    error: FilePondErrorDescription | null,
    file: FilePondFile,
  ) {
    if (error) return;

    const formData = new FormData();
    formData.append("filepond", file.serverId);
    addCsrfToken(formData);
    fetch(
      (env.REACT_APP_API_ROOT as string) + "/api/media_library/confirm_upload/",
      {
        method: "post",
        body: formData,
      },
    ).then((response) => {
      if (!response.ok) {
        showAlert(`Speichern von ${file.filename} fehlgeschlagen`, "danger");
        response.text().then(console.error);
        return;
      }
      pond.current?.removeFile(file.id);
      setSearchInput("");
      setSearch("");
      setStoredUploadsPage(0);
      setReloadCounter((counter) => counter + 1);
    });
  }

  return (
    <div className="container" style={{ margin: "auto", marginTop: "2em" }}>
      <Link to="/">
        <Button size="sm" variant="secondary">
          &lt;&lt;&nbsp;&nbsp;&nbsp;Zurück zur Übersicht
        </Button>
      </Link>
      <h1>Medienbibliothek</h1>
      <StoredUploadsCard
        uploader={
          <FilePond
            ref={pond}
            allowMultiple={true}
            allowRevert={false}
            oninit={() => onFilePondInit()}
            onprocessfile={onFileUploaded}
          />
        }
        storedUploads={storedUploads}
        searchTerm={searchInput}
        onSearchTermChange={setSearchInput}
        itemCount={storedUploadsCount}
        currentPage={storedUploadsPage}
        goToPage={setStoredUploadsPage}
        apiClient={apiClient}
        updateStoredUploadsList={updateStoredUploadsList}
      />
    </div>
  );
}
