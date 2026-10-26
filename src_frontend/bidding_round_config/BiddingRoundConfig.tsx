import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Container,
  Form,
  Modal,
  Spinner,
  Table,
} from "react-bootstrap";

import { BestellWizardApi } from "../api-client/apis/BestellWizardApi.ts";
import { BiddingRoundsApi } from "../api-client/apis/BiddingRoundsApi.ts";
import { BiddingProcedureEnum } from "../api-client/models/BiddingProcedureEnum.ts";
import { applyDisplayName } from "../bidding_round/utils/applyDisplayName.ts";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { interpolate } from "../utils/interpolate.ts";

interface BiddingRoundConfigProps {
  csrfToken: string;
}

interface ProductTypeOption {
  id: string;
  name: string;
}

interface GrowingPeriodOption {
  id: string;
  startDate: Date;
  endDate: Date;
}

function toDateInputValue(value: Date | string | null | undefined): string {
  if (!value) {
    return "";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 10);
}

function toLocalDateInputValue(
  value: Date | string | null | undefined,
): string {
  if (!value) {
    return "";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function toTimeInputValue(value: Date | string | null | undefined): string {
  if (!value) {
    return "";
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function combineToDateTime(dateValue: string, timeValue: string): Date | null {
  if (!dateValue) {
    return null;
  }
  return new Date(`${dateValue}T${timeValue || "00:00"}`);
}

function toDisplayDateTime(value: Date | string | null | undefined): string {
  const dateValue = toLocalDateInputValue(value);
  const timeValue = toTimeInputValue(value);
  if (!dateValue) {
    return "";
  }
  return `${dateValue} ${timeValue}`;
}

function statusBadge(status: string): string {
  switch (status) {
    case "active":
      return "bg-success";
    case "closed":
      return "bg-secondary";
    default:
      return "bg-warning";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "active":
      return "Aktiv";
    case "closed":
      return "Abgeschlossen";
    default:
      return "Konfiguration";
  }
}

function procedureLabel(procedure: string): string {
  return procedure === "traffic_light" ? "Ampel" : "Einfach";
}

const BiddingRoundConfig: React.FC<BiddingRoundConfigProps> = ({
  csrfToken,
}) => {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const bestellWizardApi = useApi(BestellWizardApi, csrfToken);

  const [rounds, setRounds] = useState<any[]>([]);
  const displayName: string = rounds[0]?.displayName ?? "Beitragsrunde";
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  const [growingPeriods, setGrowingPeriods] = useState<GrowingPeriodOption[]>(
    [],
  );
  const [productTypeOptions, setProductTypeOptions] = useState<
    ProductTypeOption[]
  >([]);

  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingRound, setEditingRound] = useState<any | null>(null);
  const [name, setName] = useState("");
  const [growingPeriodId, setGrowingPeriodId] = useState("");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [procedure, setProcedure] = useState("simple");
  const [bidLevels, setBidLevels] = useState(1);
  const [includeAutoRenewed, setIncludeAutoRenewed] = useState(true);
  const [comment, setComment] = useState("");
  const [selectedProductTypeId, setSelectedProductTypeId] = useState("");
  const loadRounds = () => {
    api
      .biddingRoundsApiList()
      .then((response: any) => setRounds(response))
      .catch((e) =>
        handleRequestError(
          e,
          "Runden konnten nicht geladen werden.",
          setToastDatas,
        ),
      )
      .finally(() => setLoading(false));
  };

  useEffect(loadRounds, [api]);

  const loadProductTypeOptions = (growingPeriodIdValue: string) => {
    api
      .biddingRoundsApiAvailableProductTypesList({
        growingPeriodId: growingPeriodIdValue || undefined,
      })
      .then((response: any) => setProductTypeOptions(response))
      .catch((e) =>
        handleRequestError(
          e,
          "Produkttypen konnten nicht geladen werden.",
          setToastDatas,
        ),
      );
  };

  const openCreateModal = () => {
    setEditingRound(null);
    setName("");
    setGrowingPeriodId("");
    setEndDate("");
    setEndTime("");
    setStartDate("");
    setStartTime("");
    setProcedure("simple");
    setBidLevels(1);
    setIncludeAutoRenewed(true);
    setComment("");
    setSelectedProductTypeId("");
    setShowModal(true);
    api
      .biddingRoundsApiGrowingPeriodsList()
      .then((response: any) => setGrowingPeriods(response))
      .catch((e) =>
        handleRequestError(
          e,
          "Saisons konnten nicht geladen werden.",
          setToastDatas,
        ),
      );
    loadProductTypeOptions("");
  };

  const openEditModal = (round: any) => {
    setEditingRound(round);
    setName(round.name);
    setGrowingPeriodId(round.growingPeriodId ?? "");
    setEndDate(toLocalDateInputValue(round.endAt));
    setEndTime(toTimeInputValue(round.endAt));
    setStartDate(toLocalDateInputValue(round.startAt));
    setStartTime(toTimeInputValue(round.startAt));
    setProcedure(round.biddingProcedure);
    setBidLevels(round.bidLevels ?? 1);
    setIncludeAutoRenewed(round.includeAutoRenewed);
    setComment(round.comment ?? "");
    setSelectedProductTypeId(round.product?.productTypeId ?? "");
    setShowModal(true);
    api
      .biddingRoundsApiGrowingPeriodsList()
      .then((response: any) => setGrowingPeriods(response))
      .catch((e) =>
        handleRequestError(
          e,
          "Saisons konnten nicht geladen werden.",
          setToastDatas,
        ),
      );
    loadProductTypeOptions(round.growingPeriodId ?? "");
  };

  const saveRound = async () => {
    const form = document.getElementById("roundForm") as HTMLFormElement;
    if (form && !form.reportValidity()) return;
    setSaving(true);
    try {
      if (editingRound) {
        const patchedRoundConfigRequest: any = {
          name,
          comment,
          startAt: combineToDateTime(startDate, startTime),
          endAt: combineToDateTime(endDate, endTime),
          includeAutoRenewed,
        };
        if (!editingRound.hasBids) {
          patchedRoundConfigRequest.productTypeId =
            selectedProductTypeId || null;
          patchedRoundConfigRequest.biddingProcedure = procedure as any;
          patchedRoundConfigRequest.bidLevels = bidLevels;
        }
        await api.biddingRoundsApiPartialUpdate({
          roundId: editingRound.id,
          patchedRoundConfigRequest,
        } as any);
      } else {
        await api.biddingRoundsApiCreate({
          roundCreateRequest: {
            name,
            growingPeriodId: growingPeriodId || null,
            endAt: combineToDateTime(endDate, endTime),
            startAt: combineToDateTime(startDate, startTime),
            biddingProcedure: procedure as BiddingProcedureEnum,
            bidLevels,
            includeAutoRenewed,
            comment,
            productTypeId: selectedProductTypeId || null,
          } as any,
        } as any);
      }
      setShowModal(false);
      setEditingRound(null);
      loadRounds();
    } catch (e) {
      handleRequestError(
        e,
        editingRound
          ? "Runde konnte nicht geändert werden."
          : "Runde konnte nicht erstellt werden.",
        setToastDatas,
      );
    } finally {
      setSaving(false);
    }
  };

  const deleteRound = async (round: any) => {
    if (
      !window.confirm(
        applyDisplayName(
          interpolate('Beitragsrunde "{name}" wirklich löschen?', {
            name: round.name,
          }),
          displayName,
        ),
      )
    ) {
      return;
    }
    if (
      !window.confirm(
        applyDisplayName(
          "Das Löschen kann nicht rückgängig gemacht werden. Alle Gebote dieser Beitragsrunde werden ebenfalls gelöscht. Wirklich löschen?",
          displayName,
        ),
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiDestroy({ roundId: round.id });
      loadRounds();
    } catch (e) {
      handleRequestError(
        e,
        "Runde konnte nicht gelöscht werden.",
        setToastDatas,
      );
    }
  };

  const startRound = async (roundId: string) => {
    if (
      !window.confirm(
        "Nach dem Start können Produkte und Verfahren nicht mehr geändert werden. Runde wirklich starten?",
      )
    ) {
      return;
    }
    try {
      await api.biddingRoundsApiStartCreate({ roundId });
      loadRounds();
    } catch (e) {
      handleRequestError(
        e,
        "Runde konnte nicht gestartet werden.",
        setToastDatas,
      );
    }
  };

  const closeRound = async (roundId: string) => {
    try {
      await api.biddingRoundsApiCloseCreate({ roundId });
      loadRounds();
    } catch (e) {
      handleRequestError(
        e,
        "Runde konnte nicht beendet werden.",
        setToastDatas,
      );
    }
  };

  const reopenRound = async (roundId: string) => {
    try {
      await api.biddingRoundsApiReopenCreate({ roundId });
      loadRounds();
    } catch (e) {
      handleRequestError(
        e,
        "Runde konnte nicht wieder eröffnet werden.",
        setToastDatas,
      );
    }
  };

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header className="d-flex flex-row justify-content-between align-items-center">
          <h5 className="mb-0">
            {applyDisplayName("Beitragsrunden", displayName)}
          </h5>
          <div className="d-flex flex-row">
            <TapirButton
              icon="add"
              text={applyDisplayName("Neue Beitragsrunde", displayName)}
              variant="success"
              onClick={openCreateModal}
            />
          </div>
        </Card.Header>
        <Card.Body style={{ overflow: "auto" }}>
          {loading ? (
            <div className="d-flex justify-content-center">
              <Spinner animation="border" />
            </div>
          ) : (
            <Table hover>
              <thead>
                <tr>
                  <th>{"Name"}</th>
                  <th>{"Status"}</th>
                  <th>{"Verfahren"}</th>
                  <th>{"Modus"}</th>
                  <th>{"Start"}</th>
                  <th>{"Ende"}</th>
                  <th>{"Aktionen"}</th>
                </tr>
              </thead>
              <tbody>
                {rounds.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      {applyDisplayName(
                        "Keine Beitragsrunden vorhanden.",
                        displayName,
                      )}
                    </td>
                  </tr>
                ) : (
                  rounds.map((round) => (
                    <tr key={round.id}>
                      <th className="fw-normal">{round.name}</th>
                      <td>
                        <span className={`badge ${statusBadge(round.status)}`}>
                          {statusLabel(round.status)}
                        </span>
                      </td>
                      <td>{procedureLabel(round.biddingProcedure)}</td>
                      <td>{toDisplayDateTime(round.startAt) || "–"}</td>
                      <td>{toDisplayDateTime(round.endAt)}</td>
                      <td>
                        <div className="d-flex flex-row gap-1">
                          <a
                            className="btn btn-outline-success"
                            href="/bidding_rounds/"
                          >
                            {applyDisplayName("Beitragsrunde", displayName)}
                          </a>
                          <a
                            className="btn btn-outline-primary"
                            href={`/bidding_rounds/admin/${round.id}/results`}
                          >
                            {"Auswertung"}
                          </a>
                          <Button
                            variant="outline-secondary"
                            size="sm"
                            onClick={() => openEditModal(round)}
                          >
                            {"Bearbeiten"}
                          </Button>
                          {round.status === "configuration" ||
                          round.status === "closed" ? (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => deleteRound(round)}
                            >
                              {"Löschen"}
                            </Button>
                          ) : null}
                          {round.status === "configuration" && (
                            <Button
                              variant="success"
                              size="sm"
                              onClick={() => startRound(round.id)}
                            >
                              {"Start"}
                            </Button>
                          )}
                          {round.status === "active" && (
                            <Button
                              variant="warning"
                              size="sm"
                              onClick={() => closeRound(round.id)}
                            >
                              {"Beenden"}
                            </Button>
                          )}
                          {round.status === "closed" && (
                            <Button
                              variant="success"
                              size="sm"
                              onClick={() => reopenRound(round.id)}
                            >
                              {"Wieder eröffnen"}
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        centered={true}
        size="lg"
      >
        <Modal.Header closeButton>
          <h5 className="mb-0">
            {applyDisplayName(
              editingRound ? "Beitragsrunde bearbeiten" : "Neue Beitragsrunde",
              displayName,
            )}
          </h5>
        </Modal.Header>
        <Modal.Body>
          <Form id="roundForm">
            <Form.Group className="mb-2">
              <Form.Label>{"Name"}</Form.Label>
              <Form.Control
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>{"Saison"}</Form.Label>
              <Form.Select
                value={growingPeriodId}
                onChange={(e) => {
                  setGrowingPeriodId(e.target.value);
                  loadProductTypeOptions(e.target.value);
                }}
                disabled={!!editingRound?.hasBids}
              >
                <option value={""}>{"Nächste Saison"}</option>
                {growingPeriods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {toDateInputValue(period.startDate)} –{" "}
                    {toDateInputValue(period.endDate)}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <div className="row">
              <Form.Group className="mb-2 col">
                <Form.Label>{"Start"}</Form.Label>
                <div className="d-flex gap-2">
                  <Form.Control
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                  <Form.Control
                    type="text"
                    inputMode="numeric"
                    placeholder="HH:MM"
                    pattern="([01][0-9]|2[0-3]):[0-5][0-9]"
                    title={"24-Stunden-Format, z. B. 18:30"}
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                  />
                </div>
              </Form.Group>
              <Form.Group className="mb-2 col">
                <Form.Label>{"Ende"}</Form.Label>
                <div className="d-flex gap-2">
                  <Form.Control
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    required
                  />
                  <Form.Control
                    type="text"
                    inputMode="numeric"
                    placeholder="HH:MM"
                    pattern="([01][0-9]|2[0-3]):[0-5][0-9]"
                    title={"24-Stunden-Format, z. B. 18:30"}
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    required
                  />
                </div>
              </Form.Group>
            </div>
            <Form.Group className="mb-2">
              <Form.Label>{"Bietbarer Produkttyp"}</Form.Label>
              {productTypeOptions.length === 0 ? (
                <p className="text-muted small mb-0">
                  {"Keine Produkttypen mit Kapazität in der gewählten Saison."}
                </p>
              ) : (
                <Form.Select
                  value={selectedProductTypeId}
                  onChange={(e) => setSelectedProductTypeId(e.target.value)}
                  disabled={!!editingRound?.hasBids}
                  required
                >
                  <option value="">{"Bitte wählen"}</option>
                  {productTypeOptions.map((productType) => (
                    <option key={productType.id} value={productType.id}>
                      {productType.name}
                    </option>
                  ))}
                </Form.Select>
              )}
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>{"Gebotsverfahren"}</Form.Label>
              <Form.Select
                value={procedure}
                onChange={(e) => setProcedure(e.target.value)}
                disabled={!!editingRound?.hasBids}
              >
                <option value="simple">{"Einfach"}</option>
                <option value="traffic_light">{"Ampel"}</option>
              </Form.Select>
            </Form.Group>
            {procedure === "simple" && (
              <Form.Group className="mb-2">
                <Form.Label>{"Anzahl Gebote"}</Form.Label>
                <Form.Select
                  value={bidLevels}
                  onChange={(e) => setBidLevels(Number(e.target.value))}
                  disabled={!!editingRound?.hasBids}
                >
                  <option value={1}>
                    {interpolate("{count} Gebot", {
                      count: 1,
                    })}
                  </option>
                  <option value={2}>
                    {interpolate("{count} Gebote", {
                      count: 2,
                    })}
                  </option>
                  <option value={3}>
                    {interpolate("{count} Gebote", {
                      count: 3,
                    })}
                  </option>
                </Form.Select>
              </Form.Group>
            )}
            <Form.Group className="mb-2">
              <Form.Check
                type="switch"
                label={
                  "Automatisch verlängerte Mitglieder in der Auswertung berücksichtigen"
                }
                checked={includeAutoRenewed}
                onChange={(e) => setIncludeAutoRenewed(e.target.checked)}
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>{"Kommentar"}</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </Form.Group>
            {editingRound?.hasBids && (
              <p className="text-muted small mb-0">
                {
                  "Saison, Bietverfahren, Beitragsmodus und bietbare Produkttypen können nicht mehr geändert werden, sobald Gebote abgegeben wurden."
                }
              </p>
            )}
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <TapirButton
            text={editingRound ? "Speichern" : "Anlegen"}
            icon={editingRound ? "save" : "add"}
            variant="primary"
            loading={saving}
            onClick={saveRound}
          />
        </Modal.Footer>
      </Modal>

      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </Container>
  );
};

export default BiddingRoundConfig;
