import React, { ReactNode, useEffect, useRef, useState } from "react";
import {
  Card,
  Col,
  Form,
  Modal,
  OverlayTrigger,
  Row,
  Spinner,
  Tooltip,
} from "react-bootstrap";
import {
  LocationRoute,
  PickupLocation,
  PickupLocationsApi,
  ResponseError,
} from "../api-client";
import TapirButton from "../components/TapirButton.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { HTML_ALLOWED_TEXT } from "../utils/HTML_ALLOWED_TEXT.ts";
import OpeningTimesEditor from "./OpeningTimesEditor.tsx";
import {
  API_KEYS,
  buildFormState,
  buildRequest,
  EMPTY_FORM,
  FormState,
  getDateErrors,
  getWeekdayIndex,
  OPENING_TIMES_API_KEY,
  OpeningTimeRow,
  sortOpeningTimes,
  WEEKDAYS,
} from "./pickupLocationForm.ts";

function collectMessages(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(collectMessages);
  if (value && typeof value === "object")
    return Object.values(value).flatMap(collectMessages);
  return [];
}

async function extractFieldErrors(
  error: unknown,
): Promise<Record<string, string> | null> {
  if (!(error instanceof ResponseError) || error.response.status !== 400) {
    return null;
  }
  const body = await error.response.json().catch(() => null);
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return null;
  }
  return Object.fromEntries(
    Object.entries(body).map(([field, value]) => [
      field,
      collectMessages(value).join(" "),
    ]),
  );
}

const HelpTooltip: React.FC<{ text: string }> = ({ text }) => (
  <OverlayTrigger placement={"top"} overlay={<Tooltip>{text}</Tooltip>}>
    <span
      className={"material-icons text-muted ms-1"}
      style={{ fontSize: "1rem", verticalAlign: "middle", cursor: "help" }}
    >
      info
    </span>
  </OverlayTrigger>
);

const Section: React.FC<{
  title: string;
  icon: string;
  children: ReactNode;
}> = ({ title, icon, children }) => (
  <Card className={"mb-3 shadow-sm"}>
    <Card.Header className={"d-flex align-items-center gap-2 fw-semibold"}>
      <span className={"material-icons text-primary"}>{icon}</span>
      {title}
    </Card.Header>
    <Card.Body className={"pb-2"}>{children}</Card.Body>
  </Card>
);

interface PickupLocationEditModalProps {
  show: boolean;
  onHide: () => void;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
  pickupLocationId: string | null;
  onSaved: (pickupLocation: PickupLocation) => void;
}

const PickupLocationEditModal: React.FC<PickupLocationEditModalProps> = ({
  show,
  onHide,
  csrfToken,
  setToastDatas,
  pickupLocationId,
  onSaved,
}) => {
  const api = useApi(PickupLocationsApi, csrfToken);

  const [dataLoading, setDataLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [routes, setRoutes] = useState<LocationRoute[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [openingTimes, setOpeningTimes] = useState<OpeningTimeRow[]>([]);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [initialSnapshot, setInitialSnapshot] = useState("");
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);
  const [scrollToErrorRequest, setScrollToErrorRequest] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const errors = { ...serverErrors, ...getDateErrors(form) };
  const isDirty =
    !dataLoading && JSON.stringify({ form, openingTimes }) !== initialSnapshot;

  useEffect(() => {
    if (!show) return;

    setConfirmingDiscard(false);
    setServerErrors({});
    loadData();
  }, [show, pickupLocationId]);

  useEffect(() => {
    if (scrollToErrorRequest === 0) return;

    bodyRef.current
      ?.querySelector(".is-invalid, .invalid-message")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [scrollToErrorRequest]);

  function loadData() {
    setDataLoading(true);

    Promise.all([
      api.pickupLocationsLocationRoutesList(),
      pickupLocationId === null
        ? Promise.resolve(null)
        : api.pickupLocationsPickupLocationsRetrieve({ id: pickupLocationId }),
    ])
      .then(([loadedRoutes, pickupLocation]) => {
        const loadedForm =
          pickupLocation === null ? EMPTY_FORM : buildFormState(pickupLocation);
        const loadedOpeningTimes =
          pickupLocation === null
            ? []
            : sortOpeningTimes(
                pickupLocation.openingTimes.map((openingTime) => ({
                  dayOfWeek: openingTime.dayOfWeek,
                  openTime: openingTime.openTime.substring(0, 5),
                  closeTime: openingTime.closeTime.substring(0, 5),
                })),
              );
        setRoutes(loadedRoutes);
        setForm(loadedForm);
        setOpeningTimes(loadedOpeningTimes);
        setInitialSnapshot(
          JSON.stringify({
            form: loadedForm,
            openingTimes: loadedOpeningTimes,
          }),
        );
      })
      .catch((error) =>
        handleRequestError(
          error,
          "Fehler beim Laden des Abholorts",
          setToastDatas,
        ),
      )
      .finally(() => setDataLoading(false));
  }

  function clearServerError(apiKey: string) {
    if (!(apiKey in serverErrors)) return;
    const { [apiKey]: _, ...remaining } = serverErrors;
    setServerErrors(remaining);
  }

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm({ ...form, [key]: value });
    clearServerError(API_KEYS[key]);
  }

  function updateOpeningTimes(newOpeningTimes: OpeningTimeRow[]) {
    setOpeningTimes(newOpeningTimes);
    clearServerError(OPENING_TIMES_API_KEY);
  }

  function requestClose() {
    if (confirmingDiscard) {
      setConfirmingDiscard(false);
      return;
    }
    if (isDirty) {
      setConfirmingDiscard(true);
      return;
    }
    onHide();
  }

  function onSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (Object.keys(getDateErrors(form)).length > 0) {
      setScrollToErrorRequest(scrollToErrorRequest + 1);
      return;
    }

    setSaveLoading(true);
    setServerErrors({});

    const request = buildRequest(form, openingTimes);
    const promise =
      pickupLocationId === null
        ? api.pickupLocationsPickupLocationsCreate({
            pickupLocationSaveRequestRequest: request,
          })
        : api.pickupLocationsPickupLocationsUpdate({
            id: pickupLocationId,
            pickupLocationSaveRequestRequest: request,
          });

    promise
      .then(onSaved)
      .catch(async (error) => {
        const fieldErrors = await extractFieldErrors(error);
        if (fieldErrors === null) {
          await handleRequestError(
            error,
            "Fehler beim Speichern des Abholorts",
            setToastDatas,
          );
          return;
        }
        setServerErrors(fieldErrors);
        setScrollToErrorRequest((request) => request + 1);
      })
      .finally(() => setSaveLoading(false));
  }

  function textField(
    key: Exclude<
      keyof FormState,
      "showDetailsInBasketTotalsExport" | "isHomeDelivery"
    >,
    label: string,
    options: {
      required?: boolean;
      type?: string;
      placeholder?: string;
      help?: string;
      textarea?: boolean;
      hint?: string;
    } = {},
  ) {
    const apiKey = API_KEYS[key];
    return (
      <Form.Group className={"mb-2"}>
        <Form.Label>
          {label}
          {options.required && " *"}
          {options.help && <HelpTooltip text={options.help} />}
        </Form.Label>
        {options.textarea ? (
          <Form.Control
            as={"textarea"}
            rows={2}
            placeholder={options.placeholder}
            value={form[key]}
            onChange={(event) => updateForm(key, event.target.value)}
            isInvalid={apiKey in errors}
          />
        ) : (
          <Form.Control
            type={options.type ?? "text"}
            step={options.type === "number" ? "any" : undefined}
            required={options.required}
            placeholder={options.placeholder}
            value={form[key]}
            onChange={(event) => updateForm(key, event.target.value)}
            isInvalid={apiKey in errors}
          />
        )}
        {options.hint && !(apiKey in errors) && (
          <Form.Text className={"text-muted"}>{options.hint}</Form.Text>
        )}
        <Form.Control.Feedback type={"invalid"}>
          {errors[apiKey]}
        </Form.Control.Feedback>
      </Form.Group>
    );
  }

  function getOtherErrors() {
    const knownKeys = new Set([
      ...Object.values(API_KEYS),
      OPENING_TIMES_API_KEY,
    ]);
    return Object.entries(errors).filter(([key]) => !knownKeys.has(key));
  }

  function getDateHint(date: string) {
    return date ? WEEKDAYS[getWeekdayIndex(date)] : undefined;
  }

  function getModalBody() {
    if (dataLoading) {
      return (
        <Modal.Body>
          <Spinner />
        </Modal.Body>
      );
    }

    return (
      <Modal.Body ref={bodyRef} className={"bg-body-tertiary"}>
        <Section title={"Ort"} icon={"place"}>
          <Row>
            <Col md={12}>{textField("name", "Name", { required: true })}</Col>
            <Col md={6}>
              {textField("street", "Straße & Hausnummer", {
                required: true,
                help: form.isHomeDelivery
                  ? "Bei Hauslieferung: Adresse des Depots bzw. Startpunkt der Tour."
                  : undefined,
              })}
            </Col>
            <Col md={6}>{textField("street2", "Adresszusatz")}</Col>
            <Col md={4}>
              {textField("postcode", "Postleitzahl", { required: true })}
            </Col>
            <Col md={8}>{textField("city", "Ort", { required: true })}</Col>
            <Col md={12}>
              <Form.Check
                className={"mb-2"}
                id={"is_home_delivery"}
                label={
                  <>
                    Hauslieferung
                    <HelpTooltip
                      text={
                        "Die Mitglieder werden an ihre eigene Adresse beliefert, statt an diesem Ort abzuholen."
                      }
                    />
                  </>
                }
                checked={form.isHomeDelivery}
                onChange={(event) =>
                  updateForm("isHomeDelivery", event.target.checked)
                }
              />
            </Col>
            {!form.isHomeDelivery && (
              <>
                <Col md={6}>
                  {textField("latitude", "Breitengrad", {
                    required: true,
                    type: "number",
                    placeholder: "z.B. 53.2731785",
                  })}
                </Col>
                <Col md={6}>
                  {textField("longitude", "Längengrad", {
                    required: true,
                    type: "number",
                    placeholder: "z.B. 10.3741756",
                  })}
                </Col>
              </>
            )}
          </Row>
        </Section>

        <Section title={"Abholung"} icon={"schedule"}>
          <Form.Label>Abholzeiten *</Form.Label>
          <OpeningTimesEditor
            openingTimes={openingTimes}
            onChange={updateOpeningTimes}
            error={errors[OPENING_TIMES_API_KEY]}
          />
          <Row className={"mt-2"}>
            <Col md={12}>
              {textField("info", "Zusätzliche Informationen zur Abholung", {
                textarea: true,
                placeholder: "z.B.: im Hinterhof",
                help: `${HTML_ALLOWED_TEXT} Max. 3000 Zeichen inkl. HTML-Tags.`,
              })}
            </Col>
            {!form.isHomeDelivery && (
              <Col md={6}>{textField("accessCode", "Zugangscode")}</Col>
            )}
            <Col md={6}>
              {textField("contactName", "Name der Abholort-Pat*innen")}
            </Col>
            {!form.isHomeDelivery && (
              <Col md={6}>
                {textField("messengerGroupLink", "Link zur Messenger-Gruppe")}
              </Col>
            )}
            <Col md={6}>
              {textField("photoLink", "Link zum Foto des Abholorts")}
            </Col>
          </Row>
        </Section>

        <Section title={"Betriebszeitraum"} icon={"event"}>
          <Row>
            <Col md={6}>
              {textField("startDate", "Verfügbar ab", {
                type: "date",
                help: "Leer = ab sofort verfügbar. Neuanlagen nur an einem Montag möglich.",
                hint: getDateHint(form.startDate),
              })}
            </Col>
            <Col md={6}>
              {textField("endDate", "Verfügbar bis", {
                type: "date",
                help: "Leer = dauerhaft verfügbar. Schließen nur an einem Sonntag möglich.",
                hint: getDateHint(form.endDate),
              })}
            </Col>
          </Row>
        </Section>

        <Section title={"Logistik"} icon={"local_shipping"}>
          <Row>
            <Col md={6}>
              <Form.Group className={"mb-2"}>
                <Form.Label>Ausfahrrunde</Form.Label>
                <Form.Select
                  value={form.locationRouteId}
                  onChange={(event) =>
                    updateForm("locationRouteId", event.target.value)
                  }
                  isInvalid={API_KEYS.locationRouteId in errors}
                >
                  <option value={""}>Keine</option>
                  {routes.map((route) => (
                    <option key={route.id} value={route.id}>
                      {route.name}
                    </option>
                  ))}
                </Form.Select>
                <Form.Control.Feedback type={"invalid"}>
                  {errors[API_KEYS.locationRouteId]}
                </Form.Control.Feedback>
              </Form.Group>
            </Col>
            <Col md={12}>
              {textField("routeInfo", "Information Fahrer", {
                textarea: true,
                placeholder:
                  "z.B.: kleine Kisten links abstellen; große Tauschkiste",
                help: "Max. 3000 Zeichen.",
              })}
            </Col>
            <Col md={12}>
              <Form.Check
                id={"show_details_in_basket_totals_export"}
                label={"Im Gesamtkistenanzahls-Zettel Details anzeigen"}
                checked={form.showDetailsInBasketTotalsExport}
                onChange={(event) =>
                  updateForm(
                    "showDetailsInBasketTotalsExport",
                    event.target.checked,
                  )
                }
              />
            </Col>
          </Row>
        </Section>

        {getOtherErrors().map(([key, message]) => (
          <div className={"invalid-message text-danger small mt-2"} key={key}>
            {message}
          </div>
        ))}
      </Modal.Body>
    );
  }

  const errorCount = Object.keys(errors).length;

  function buildDiscardConfirmation() {
    return (
      <>
        <Modal.Header closeButton>
          <h5 className={"mb-0"}>Ungespeicherte Änderungen</h5>
        </Modal.Header>
        <Modal.Body>
          Die Änderungen wurden nicht gespeichert. Trotzdem schließen?
        </Modal.Body>
        <Modal.Footer className={"justify-content-between"}>
          <TapirButton
            variant={"outline-secondary"}
            icon={"arrow_back"}
            text={"Abbrechen"}
            onClick={() => setConfirmingDiscard(false)}
          />
          <TapirButton
            variant={"danger"}
            icon={"close"}
            text={"Verwerfen"}
            onClick={onHide}
          />
        </Modal.Footer>
      </>
    );
  }

  return (
    <Modal
      show={show}
      onHide={requestClose}
      centered={true}
      size={confirmingDiscard ? undefined : "lg"}
      scrollable={true}
    >
      {confirmingDiscard ? (
        buildDiscardConfirmation()
      ) : (
        <Form onSubmit={onSave} style={{ display: "contents" }}>
          <Modal.Header closeButton>
            <h5 className={"mb-0"}>
              {pickupLocationId === null
                ? "Abholort hinzufügen"
                : "Abholort bearbeiten"}
            </h5>
          </Modal.Header>
          {getModalBody()}
          <Modal.Footer className={"justify-content-between"}>
            <span className={"text-danger small"}>
              {errorCount > 0 && `${errorCount} Fehler – bitte prüfen`}
            </span>
            <TapirButton
              variant={"primary"}
              icon={"save"}
              text={"Speichern"}
              type={"submit"}
              loading={saveLoading}
              disabled={dataLoading}
            />
          </Modal.Footer>
        </Form>
      )}
    </Modal>
  );
};

export default PickupLocationEditModal;
