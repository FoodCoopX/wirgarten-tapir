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
import {
  formatEuroNumber,
  parseEuroAmount,
} from "../bidding_round/utils/bidLevels.ts";
import TapirButton from "../components/TapirButton.tsx";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";
import { interpolate } from "../utils/interpolate.ts";

interface BiddingRoundConfigProps {
  csrfToken: string;
}

interface ProductOption {
  id: string;
  name: string;
  size?: string | number | null;
}

interface ProductTypeOption {
  id: string;
  name: string;
  products: ProductOption[];
}

interface PriceInput {
  productId: string;
  productName: string;
  referenceValue: string;
  minAmount: string;
  size: number;
}

function parseProductSize(value: string | number | null | undefined): number {
  if (value === null || value === undefined) {
    return 1;
  }
  const parsed = typeof value === "number" ? value : Number.parseFloat(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

interface GrowingPeriodOption {
  id: string;
  startDate: Date;
  endDate: Date;
}

function buildPriceInputs(
  products: ProductOption[] | undefined,
  existingPrices?: {
    productId: string;
    referenceValue?: string | null;
    minAmount?: string | null;
  }[],
): PriceInput[] {
  return (products ?? []).map((product) => {
    const existing = existingPrices?.find(
      (price) => price.productId === product.id,
    );
    return {
      productId: product.id,
      productName: product.name,
      referenceValue: existing?.referenceValue ?? "",
      minAmount: existing?.minAmount ?? "",
      size: parseProductSize(product.size),
    };
  });
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
  const [targetAmountPerYear, setTargetAmountPerYear] = useState("");
  const [priceInputs, setPriceInputs] = useState<PriceInput[]>([]);
  const valuesLocked = !!editingRound?.hasBids;

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
    return api
      .biddingRoundsApiAvailableProductTypesList({
        growingPeriodId: growingPeriodIdValue || undefined,
      })
      .then((response: any) => {
        setProductTypeOptions(response);
        return response as ProductTypeOption[];
      })
      .catch((e) => {
        handleRequestError(
          e,
          "Produkttypen konnten nicht geladen werden.",
          setToastDatas,
        );
        return [] as ProductTypeOption[];
      });
  };

  const selectProductType = (productTypeId: string, existingPrices?: any[]) => {
    setSelectedProductTypeId(productTypeId);
    const productType = productTypeOptions.find(
      (option) => option.id === productTypeId,
    );
    setPriceInputs(buildPriceInputs(productType?.products, existingPrices));
  };

  const updatePriceInput = (
    index: number,
    field: "referenceValue" | "minAmount",
    value: string,
  ) => {
    setPriceInputs((previous) => {
      const edited = previous[index];
      const parsedValue = parseEuroAmount(value);
      return previous.map((input, currentIndex) => {
        if (currentIndex === index) {
          return { ...input, [field]: value };
        }
        // Pre-fill sizes that are still empty proportionally to the edited one, so
        // the admin does not have to compute the per-size values by hand. Values
        // that were already entered are never overwritten.
        if (input[field] !== "" || parsedValue === null || edited.size <= 0) {
          return input;
        }
        return {
          ...input,
          [field]: formatEuroNumber((parsedValue * input.size) / edited.size),
        };
      });
    });
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
    setTargetAmountPerYear("");
    setPriceInputs([]);
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
    setTargetAmountPerYear(round.product?.targetAmountPerYear ?? "");
    setPriceInputs([]);
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
    loadProductTypeOptions(round.growingPeriodId ?? "").then(
      (productTypeOptions: ProductTypeOption[]) => {
        const productType = productTypeOptions.find(
          (option) => option.id === round.product?.productTypeId,
        );
        setSelectedProductTypeId(round.product?.productTypeId ?? "");
        setPriceInputs(
          buildPriceInputs(productType?.products, round.product?.prices),
        );
      },
    );
  };

  const buildPricesPayload = () =>
    priceInputs.map((input) => ({
      productId: input.productId,
      referenceValue: input.referenceValue || null,
      minAmount: input.minAmount || null,
    }));

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
          patchedRoundConfigRequest.targetAmountPerYear =
            targetAmountPerYear || null;
          patchedRoundConfigRequest.prices = buildPricesPayload();
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
            targetAmountPerYear: targetAmountPerYear || null,
            prices: buildPricesPayload(),
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
                  <th>{"Start"}</th>
                  <th>{"Ende"}</th>
                  <th>{"Aktionen"}</th>
                </tr>
              </thead>
              <tbody>
                {rounds.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
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
                              disabled={
                                round.product?.targetAmountPerYear == null
                              }
                              title={
                                round.product?.targetAmountPerYear == null
                                  ? "Zielbetrag pro Jahr muss zuerst gesetzt werden."
                                  : undefined
                              }
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
                  onChange={(e) => selectProductType(e.target.value)}
                  disabled={valuesLocked}
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
            {selectedProductTypeId && (
              <>
                <Form.Group className="mb-2">
                  <Form.Label>{"Zielbetrag pro Jahr (€)"}</Form.Label>
                  <Form.Control
                    type="text"
                    inputMode="decimal"
                    placeholder="z. B. 220800"
                    value={targetAmountPerYear}
                    onChange={(e) => setTargetAmountPerYear(e.target.value)}
                    disabled={valuesLocked}
                  />
                  <Form.Text className="text-muted">
                    {
                      "Wird für die Deckungs-Auswertung der Runde benötigt und muss vor dem Start gesetzt sein."
                    }
                  </Form.Text>
                </Form.Group>
                <Form.Group className="mb-2">
                  <Form.Label>
                    {"Ernteanteile: Richtwert und Mindestpreis (€/Monat)"}
                  </Form.Label>
                  {priceInputs.length === 0 ? (
                    <p className="text-muted small mb-0">
                      {"Keine Ernteanteile für diesen Produkttyp gefunden."}
                    </p>
                  ) : (
                    <Table size="sm" borderless className="mb-0">
                      <thead>
                        <tr>
                          <th>{"Ernteanteil"}</th>
                          <th>{"Richtwert"}</th>
                          <th>{"Mindestpreis"}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {priceInputs.map((input, index) => (
                          <tr key={input.productId}>
                            <td className="align-middle">
                              {input.productName}
                            </td>
                            <td>
                              <Form.Control
                                type="text"
                                inputMode="decimal"
                                value={input.referenceValue}
                                disabled={valuesLocked}
                                onChange={(e) =>
                                  updatePriceInput(
                                    index,
                                    "referenceValue",
                                    e.target.value,
                                  )
                                }
                              />
                            </td>
                            <td>
                              <Form.Control
                                type="text"
                                inputMode="decimal"
                                value={input.minAmount}
                                disabled={valuesLocked}
                                onChange={(e) =>
                                  updatePriceInput(
                                    index,
                                    "minAmount",
                                    e.target.value,
                                  )
                                }
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Form.Group>
              </>
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
                  "Saison, Bietverfahren, Anzahl Gebote, bietbare Produkttypen und die Bietrunden-Werte (Zielbetrag, Richtwert, Mindestpreis) können nicht mehr geändert werden, sobald Gebote abgegeben wurden."
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
