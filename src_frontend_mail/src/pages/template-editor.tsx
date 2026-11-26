import { IEmailTemplate } from "easy-email-editor";
import { useEffect, useRef, useState } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";
import { useNavigate, useParams } from "react-router-dom";
import { TapirmailApi, TemplateTypeEnum } from "tapir-api-client";
import Editor, { EMPTY_LAYOUT_PAGE, EMPTY_PAGE } from "../components/editor";
import LabelHelp from "../components/LabelHelp";
import Loading from "../components/loading";
import { useAlert } from "../contexts/alerts";
import { useApi } from "../hooks/useApi";
import { usePreventUnload } from "../hooks/usePreventUnload";
import { getApiErrorMessage } from "../utils/apiErrorMessage";
import {
  containsLayoutBodySection,
  jsonToMjml,
  markLayoutBodyBlocks,
  mjmlToJson,
} from "../utils/mjml";

const TemplateEditor = () => {
  usePreventUnload();
  const showAlert = useAlert();
  const navigate = useNavigate();
  const api = useApi(TapirmailApi);

  const { templateId } = useParams();

  const [id, setId] = useState(templateId);
  const [name, setName] = useState("");
  const [templateType, setTemplateType] = useState<TemplateTypeEnum>(
    TemplateTypeEnum.Start,
  );
  const [isDefaultLayout, setIsDefaultLayout] = useState(false);
  const [content, setContent] = useState<any>(EMPTY_PAGE);
  const [savedContent, setSavedContent] = useState<any>(EMPTY_PAGE);
  const [savedName, setSavedName] = useState("");
  const [savedTemplateType, setSavedTemplateType] = useState<TemplateTypeEnum>(
    TemplateTypeEnum.Start,
  );
  const [savedIsDefaultLayout, setSavedIsDefaultLayout] = useState(false);
  const [hasLayoutBodyBlock, setHasLayoutBodyBlock] = useState(false);
  const latestEditorContent = useRef<any>(EMPTY_PAGE);
  const [showSaveGateModal, setShowSaveGateModal] = useState(false);
  const [loading, setLoading] = useState(Boolean(id));
  const [sourceMode, setSourceMode] = useState<"mjml" | "json" | null>(null);
  const [sourceText, setSourceText] = useState("");
  const [sourceError, setSourceError] = useState("");

  useEffect(() => {
    if (!id || !api || !showAlert || !navigate) return;

    setLoading(true);
    api
      .tapirmailApiEmailTemplateRetrieve({ id: id })
      .then((data) => {
        const loadedTemplateType = data.templateType ?? TemplateTypeEnum.Start;
        const loadedContent =
          loadedTemplateType === TemplateTypeEnum.Layout
            ? markLayoutBodyBlocks(mjmlToJson(data.content))
            : mjmlToJson(data.content);
        setContent(loadedContent);
        setSavedContent(loadedContent);
        setHasLayoutBodyBlock(containsLayoutBodySection(loadedContent));
        setId(data.id);
        setName(data.name);
        setSavedName(data.name);
        setTemplateType(loadedTemplateType);
        setSavedTemplateType(loadedTemplateType);
        const loadedIsDefaultLayout = data.isDefaultLayout ?? false;
        setIsDefaultLayout(loadedIsDefaultLayout);
        setSavedIsDefaultLayout(loadedIsDefaultLayout);
        setLoading(false);
      })
      .catch(async (err) => {
        console.error(err);
        showAlert(
          await getApiErrorMessage(err, "Fehler beim Laden der Vorlage"),
          "danger",
        );
        navigate("/");
      });
  }, [id]);

  const hasMetadataChanges =
    name !== savedName ||
    templateType !== savedTemplateType ||
    isDefaultLayout !== savedIsDefaultLayout;

  const handleBack = (values: IEmailTemplate) => {
    if (values.content === savedContent && !hasMetadataChanges) {
      navigate("/");
    } else {
      setShowSaveGateModal(true);
    }
  };

  const handleSave = (values: IEmailTemplate) => {
    const contentMjml = jsonToMjml(values.content);

    if (
      templateType === TemplateTypeEnum.Layout &&
      !containsLayoutBodySection(values.content)
    ) {
      showAlert(
        "Der E-Mail-Inhalt-Block fehlt. Layout-Vorlagen brauchen genau einen.",
        "danger",
      );
      return;
    }

    const props = {
      emailTemplateRequest: {
        name: name,
        content: contentMjml,
        templateType: templateType,
        isDefaultLayout:
          templateType === TemplateTypeEnum.Layout ? isDefaultLayout : false,
      },
    };
    if (templateId) {
      api
        .tapirmailApiEmailTemplateUpdate({
          id: templateId,
          ...props,
        })
        .then((data) => {
          showAlert("Deine Änderungen wurden gespeichert!", "success");
          setContent(values.content);
          setSavedContent(values.content);
          setSavedName(name);
          setSavedTemplateType(templateType);
          setSavedIsDefaultLayout(isDefaultLayout);
        })
        .catch(async (err) => {
          showAlert(
            await getApiErrorMessage(
              err,
              "Beim Speichern ist ein Fehler aufgetreten.",
            ),
            "danger",
          );
        });
    } else {
      api
        .tapirmailApiEmailTemplateCreate(props)
        .then((data) => {
          showAlert("Deine Vorlage wurde gespeichert!", "success");
          if (data.id) {
            navigate("/editor/" + data.id);
          }
        })
        .catch(async (err) => {
          showAlert(
            await getApiErrorMessage(
              err,
              "Beim Speichern ist ein Fehler aufgetreten.",
            ),
            "danger",
          );
        });
    }
  };

  const handleCloseModal = () => setShowSaveGateModal(false);
  const openSourceEditor = (mode: "mjml" | "json") => {
    setSourceMode(mode);
    setSourceError("");
    setSourceText(
      mode === "mjml"
        ? jsonToMjml(latestEditorContent.current)
        : JSON.stringify(latestEditorContent.current, null, 2),
    );
  };

  const closeSourceEditor = () => {
    setSourceMode(null);
    setSourceError("");
  };

  const applySource = () => {
    try {
      const parsed =
        sourceMode === "mjml" ? mjmlToJson(sourceText) : JSON.parse(sourceText);
      if (
        !parsed ||
        parsed.type !== "page" ||
        !Array.isArray(parsed.children)
      ) {
        throw new Error("Der Quelltext enthält keine gültige Vorlage.");
      }

      const nextContent =
        templateType === TemplateTypeEnum.Layout
          ? markLayoutBodyBlocks(parsed)
          : parsed;

      if (
        templateType === TemplateTypeEnum.Layout &&
        !containsLayoutBodySection(nextContent)
      ) {
        throw new Error(
          "Eine Layout-Vorlage muss genau einen E-Mail-Inhalt-Block enthalten.",
        );
      }
      setContent(nextContent);
      setHasLayoutBodyBlock(containsLayoutBodySection(nextContent));
      closeSourceEditor();
    } catch (error) {
      setSourceError(
        error instanceof Error
          ? error.message
          : "Der Quelltext konnte nicht gelesen werden.",
      );
    }
  };
  return (
    <>
      <div
        style={{
          display: "flex",
          gap: "2em",
          alignItems: "center",
          padding: "0.5em 1em",
        }}
      >
        <Form.Group>
          <Form.Label>Vorlagen-Typ</Form.Label>
          <Form.Control
            as="select"
            value={templateType}
            onChange={(event) => {
              const newType = event.target.value as TemplateTypeEnum;
              setTemplateType(newType);
              if (
                newType === TemplateTypeEnum.Layout &&
                (latestEditorContent.current?.children?.length ?? 0) === 0
              ) {
                setContent(EMPTY_LAYOUT_PAGE);
                setHasLayoutBodyBlock(true);
              }
            }}
          >
            <option value={TemplateTypeEnum.Start}>Start-Vorlage</option>
            <option value={TemplateTypeEnum.Layout}>Layout-Vorlage</option>
          </Form.Control>
          <Form.Text className="text-muted">
            {templateType === TemplateTypeEnum.Layout
              ? "Einheitliches Aussehen wie Kopf- und Fußzeile, wird beim Versand angewendet."
              : "Kopiert den Inhalt in neue E-Mails."}
          </Form.Text>
        </Form.Group>
        {templateType === TemplateTypeEnum.Layout && (
          <>
            <Form.Group controlId="is-default-layout" className="mb-0">
              <Form.Check type="checkbox">
                <Form.Check.Input
                  type="checkbox"
                  checked={isDefaultLayout}
                  onChange={(event) => setIsDefaultLayout(event.target.checked)}
                />
                <Form.Check.Label
                  onClick={(event) => {
                    event.preventDefault();
                    setIsDefaultLayout((value) => !value);
                  }}
                >
                  Als Standard-Layout verwenden
                  <LabelHelp
                    label="Standard-Layout"
                    text="Wird automatisch für neue E-Mails verwendet. Nur ein Standard-Layout möglich."
                  />
                </Form.Check.Label>
              </Form.Check>
            </Form.Group>
            <span>
              Block <strong>E-Mail-Inhalt</strong> an die gewünschte Stelle
              ziehen. Er ist nur einmal erlaubt.
            </span>
          </>
        )}
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => openSourceEditor("mjml")}
        >
          MJML-Quelltext
        </Button>
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => openSourceEditor("json")}
        >
          JSON-Quelltext
        </Button>
      </div>
      <Modal
        show={sourceMode !== null}
        onHide={closeSourceEditor}
        centered={true}
        size="xl"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {sourceMode === "mjml"
              ? "MJML-Quelltext bearbeiten"
              : "JSON-Quelltext bearbeiten"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p className="text-muted">
            Beim Übernehmen wird der Inhalt des Editors vollständig durch den
            Quelltext ersetzt. Layout-Vorlagen benötigen genau einen
            E-Mail-Inhalt-Block.
          </p>
          <Form.Control
            as="textarea"
            rows={22}
            value={sourceText}
            onChange={(event) => setSourceText(event.target.value)}
            spellCheck={false}
            style={{ fontFamily: "monospace", fontSize: "0.85rem" }}
          />
          {sourceError && (
            <Alert variant="danger" className="mt-3 mb-0">
              {sourceError}
            </Alert>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={closeSourceEditor}>
            Abbrechen
          </Button>
          <Button variant="primary" onClick={applySource}>
            Übernehmen
          </Button>
        </Modal.Footer>
      </Modal>
      <Modal show={showSaveGateModal} onHide={handleCloseModal} centered={true}>
        <Modal.Header closeButton>
          <Modal.Title>Achtung!</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Du hast <strong>ungespeicherte Änderungen</strong>!<br />
          Möchtest du deine Änderungen wirklich verwerfen?
        </Modal.Body>
        <Modal.Footer
          style={{ display: "flex", justifyContent: "space-between" }}
        >
          <Button variant="danger" onClick={() => navigate("/")}>
            Änderungen verwerfen
          </Button>
          <Button variant="success" onClick={handleCloseModal}>
            Weiter Editieren
          </Button>
        </Modal.Footer>
      </Modal>
      {loading ? (
        <Loading />
      ) : (
        <Editor
          onGoBack={handleBack}
          onSave={handleSave}
          onTemplateNameChange={(name) => setName(name)}
          templateName={name}
          content={content}
          showLayoutBodyBlock={templateType === TemplateTypeEnum.Layout}
          layoutBodyBlockExists={hasLayoutBodyBlock}
          hasUnsavedChanges={hasMetadataChanges}
          onContentChange={(values) => {
            latestEditorContent.current = values.content;
            setHasLayoutBodyBlock(containsLayoutBodySection(values.content));
          }}
        />
      )}
    </>
  );
};

export default TemplateEditor;
