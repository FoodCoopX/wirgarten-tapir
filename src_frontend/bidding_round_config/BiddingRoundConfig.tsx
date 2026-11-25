import React, { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Container,
  Form,
  Modal,
  Row,
  Spinner,
  Table,
} from "react-bootstrap";

import { BiddingRoundsApi } from "../api-client/apis/BiddingRoundsApi.ts";
import { BiddingProcedureEnum } from "../api-client/models/BiddingProcedureEnum.ts";
import { GrowingPeriodOption } from "../api-client/models/GrowingPeriodOption.ts";
import { PatchedRoundConfigRequest } from "../api-client/models/PatchedRoundConfigRequest.ts";
import { ProductTypeOption } from "../api-client/models/ProductTypeOption.ts";
import { Round } from "../api-client/models/Round.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import { useApi } from "../hooks/useApi.ts";
import { ToastData } from "../types/ToastData.ts";
import { addToast } from "../utils/addToast.ts";
import { handleRequestError } from "../utils/handleRequestError.ts";

interface BiddingRoundConfigProps {
  csrfToken: string;
}

interface PriceDraft {
  referenceValue: string;
  minAmount: string;
  size: string;
}

interface FormState {
  name: string;
  growingPeriodId: string;
  startAt: string;
  endAt: string;
  comment: string;
  productTypeId: string;
  targetAmountPerYear: string;
  biddingProcedure: string;
  bidLevels: string;
  includeAutoRenewed: boolean;
  prices: Record<string, PriceDraft>;
}

const EMPTY_FORM: FormState = {
  name: "",
  growingPeriodId: "",
  startAt: "",
  endAt: "",
  comment: "",
  productTypeId: "",
  targetAmountPerYear: "",
  biddingProcedure: "simple",
  bidLevels: "1",
  includeAutoRenewed: true,
  prices: {},
};

function toInputValue(date: Date | null): string {
  if (!date) {
    return "";
  }
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}

const BiddingRoundConfig: React.FC<BiddingRoundConfigProps> = ({
  csrfToken,
}) => {
  const api = useApi(BiddingRoundsApi, csrfToken);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [periods, setPeriods] = useState<GrowingPeriodOption[]>([]);
  const [productTypes, setProductTypes] = useState<ProductTypeOption[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingRoundId, setEditingRoundId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [loadedRounds, loadedPeriods] = await Promise.all([
        api.biddingRoundsApiList(),
        api.biddingRoundsApiGrowingPeriodsList(),
      ]);
      setRounds(loadedRounds);
      setPeriods(loadedPeriods);
    } catch (error) {
      await handleRequestError(
        error,
        "Die Beitragsrunden konnten nicht geladen werden.",
        setToastDatas,
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadProductTypes(growingPeriodId: string) {
    if (!growingPeriodId) {
      setProductTypes([]);
      return;
    }
    try {
      setProductTypes(
        await api.biddingRoundsApiAvailableProductTypesList({
          growingPeriodId,
        }),
      );
    } catch (error) {
      await handleRequestError(
        error,
        "Die Produkttypen konnten nicht geladen werden.",
        setToastDatas,
      );
    }
  }

  function updateForm(field: keyof FormState, value: string) {
    setForm((current) => {
      const next = { ...current, [field]: value };
      if (field === "biddingProcedure" && value === "bid_range") {
        next.bidLevels = "2";
      }
      if (field === "productTypeId") {
        const productType = productTypes.find((type) => type.id === value);
        const prices: Record<string, PriceDraft> = {};
        for (const product of productType?.products ?? []) {
          prices[product.id] = current.prices[product.id] ?? {
            referenceValue: "",
            minAmount: "",
            size: "",
          };
        }
        next.prices = prices;
      }
      return next;
    });
    if (field === "growingPeriodId") {
      void loadProductTypes(value);
    }
  }

  function updatePrice(
    productId: string,
    field: keyof PriceDraft,
    value: string,
  ) {
    setForm((current) => ({
      ...current,
      prices: {
        ...current.prices,
        [productId]: {
          ...current.prices[productId],
          [field]: value,
        },
      },
    }));
  }

  function resetForm() {
    setEditingRoundId(null);
    setForm(EMPTY_FORM);
    setProductTypes([]);
  }

  function openCreateModal() {
    resetForm();
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    resetForm();
  }

  function editRound(round: Round) {
    setEditingRoundId(round.id);
    const prices: Record<string, PriceDraft> = {};
    for (const price of round.product?.prices ?? []) {
      prices[price.productId] = {
        referenceValue: price.referenceValue ?? "",
        minAmount: price.minAmount ?? "",
        size: price.size ?? "",
      };
    }
    setForm({
      name: round.name,
      growingPeriodId: round.growingPeriodId ?? "",
      startAt: toInputValue(round.startAt),
      endAt: toInputValue(round.endAt),
      comment: round.comment,
      productTypeId: round.product?.productTypeId ?? "",
      targetAmountPerYear: round.product?.targetAmountPerYear ?? "",
      biddingProcedure: round.biddingProcedure,
      bidLevels: String(round.bidLevels),
      includeAutoRenewed: round.includeAutoRenewed,
      prices,
    });
    void loadProductTypes(round.growingPeriodId ?? "");
    setShowModal(true);
  }

  function buildPatch(
    prices: {
      productId: string;
      referenceValue: string | null;
      minAmount: string | null;
      size: string;
    }[],
  ): PatchedRoundConfigRequest {
    const current = rounds.find((round) => round.id === editingRoundId);
    const patch: PatchedRoundConfigRequest = {
      name: form.name,
      comment: form.comment,
      startAt: form.startAt ? new Date(form.startAt) : null,
      endAt: form.endAt ? new Date(form.endAt) : undefined,
    };
    if (!current) {
      return patch;
    }
    if (form.productTypeId !== (current.product?.productTypeId ?? "")) {
      patch.productTypeId = form.productTypeId || null;
    }
    if (
      form.targetAmountPerYear !== (current.product?.targetAmountPerYear ?? "")
    ) {
      patch.targetAmountPerYear = form.targetAmountPerYear || null;
    }
    const currentPrices = (current.product?.prices ?? []).map((price) => ({
      productId: price.productId,
      referenceValue: price.referenceValue ?? null,
      minAmount: price.minAmount ?? null,
      size: price.size ?? "",
    }));
    if (JSON.stringify(currentPrices) !== JSON.stringify(prices)) {
      patch.prices = prices;
    }
    if (form.biddingProcedure !== current.biddingProcedure) {
      patch.biddingProcedure = (form.biddingProcedure ||
        "simple") as BiddingProcedureEnum;
    }
    const formBidLevels =
      form.biddingProcedure === "bid_range" ? 2 : Number(form.bidLevels) || 1;
    if (formBidLevels !== current.bidLevels) {
      patch.bidLevels = formBidLevels;
    }
    if (form.includeAutoRenewed !== current.includeAutoRenewed) {
      patch.includeAutoRenewed = form.includeAutoRenewed;
    }
    return patch;
  }

  async function saveRound() {
    const prices = Object.entries(form.prices).map(([productId, price]) => ({
      productId,
      referenceValue: price.referenceValue || null,
      minAmount: price.minAmount || null,
      size: price.size,
    }));

    try {
      if (editingRoundId) {
        await api.biddingRoundsApiPartialUpdate({
          roundId: editingRoundId,
          patchedRoundConfigRequest: buildPatch(prices),
        });
      } else {
        await api.biddingRoundsApiCreate({
          roundCreateRequest: {
            growingPeriodId: form.growingPeriodId || null,
            name: form.name,
            startAt: form.startAt ? new Date(form.startAt) : null,
            endAt: new Date(form.endAt),
            comment: form.comment,
            productTypeId: form.productTypeId || null,
            targetAmountPerYear: form.targetAmountPerYear || null,
            biddingProcedure: (form.biddingProcedure ||
              "simple") as BiddingProcedureEnum,
            bidLevels:
              form.biddingProcedure === "bid_range"
                ? 2
                : Number(form.bidLevels) || 1,
            includeAutoRenewed: form.includeAutoRenewed,
            prices,
          },
        });
      }
      addToast(
        {
          title: "Gespeichert",
          variant: "success",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      setShowModal(false);
      resetForm();
      await load();
    } catch (error) {
      await handleRequestError(
        error,
        "Die Beitragsrunde konnte nicht gespeichert werden.",
        setToastDatas,
      );
    }
  }

  async function runAction(
    action: () => Promise<unknown>,
    successMessage: string,
  ) {
    try {
      await action();
      addToast(
        {
          title: successMessage,
          variant: "success",
          id: crypto.randomUUID(),
        },
        setToastDatas,
      );
      await load();
    } catch (error) {
      await handleRequestError(
        error,
        "Die Aktion ist fehlgeschlagen.",
        setToastDatas,
      );
    }
  }

  if (loading) {
    return (
      <Container className={"py-5 text-center"}>
        <Spinner animation={"border"} />
      </Container>
    );
  }

  const selectedProductType = productTypes.find(
    (type) => type.id === form.productTypeId,
  );

  const selectedPrices = selectedProductType
    ? selectedProductType.products
        .map((product) => form.prices[product.id])
        .filter((price) => price !== undefined)
    : [];
  const hasInvalidSize = selectedPrices.some(
    (price) => !price.size || Number.parseFloat(price.size) <= 0,
  );
  const canEditSensitive = !editingRoundId
    ? true
    : !(rounds.find((round) => round.id === editingRoundId)?.hasBids ?? false);

  return (
    <Container fluid className={"py-4"}>
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
      <div className={"d-flex justify-content-between align-items-center mb-4"}>
        <h1 className={"mb-0"}>Beitragsrunden</h1>
        <Button variant={"dark"} onClick={openCreateModal}>
          Neue Beitragsrunde
        </Button>
      </div>

      <Modal show={showModal} onHide={closeModal} size={"lg"}>
        <Modal.Header closeButton>
          <Modal.Title>
            {editingRoundId ? "Beitragsrunde bearbeiten" : "Neue Beitragsrunde"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Row className={"g-3"}>
            <Col md={6}>
              <Form.Group>
                <Form.Label>Name</Form.Label>
                <Form.Control
                  value={form.name}
                  onChange={(event) => updateForm("name", event.target.value)}
                />
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group>
                <Form.Label>Vertragsperiode</Form.Label>
                <Form.Select
                  value={form.growingPeriodId}
                  disabled={editingRoundId !== null}
                  onChange={(event) =>
                    updateForm("growingPeriodId", event.target.value)
                  }
                >
                  <option value={""}>Bitte wählen</option>
                  {periods.map((period) => (
                    <option key={period.id} value={period.id}>
                      {new Date(period.startDate).toLocaleDateString("de-DE")} –{" "}
                      {new Date(period.endDate).toLocaleDateString("de-DE")}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Start</Form.Label>
                <Form.Control
                  type={"datetime-local"}
                  value={form.startAt}
                  onChange={(event) =>
                    updateForm("startAt", event.target.value)
                  }
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Ende</Form.Label>
                <Form.Control
                  type={"datetime-local"}
                  value={form.endAt}
                  onChange={(event) => updateForm("endAt", event.target.value)}
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Zielbetrag pro Jahr (€)</Form.Label>
                <Form.Control
                  value={form.targetAmountPerYear}
                  onChange={(event) =>
                    updateForm("targetAmountPerYear", event.target.value)
                  }
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Check
                  type={"checkbox"}
                  label={"Auto-Verlängerte einbeziehen"}
                  checked={form.includeAutoRenewed}
                  disabled={!canEditSensitive}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      includeAutoRenewed: event.target.checked,
                    }))
                  }
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Produkttyp</Form.Label>
                <Form.Select
                  value={form.productTypeId}
                  disabled={!canEditSensitive}
                  onChange={(event) =>
                    updateForm("productTypeId", event.target.value)
                  }
                >
                  <option value={""}>Bitte wählen</option>
                  {productTypes.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.name}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Verfahren</Form.Label>
                <Form.Select
                  value={form.biddingProcedure}
                  disabled={!canEditSensitive}
                  onChange={(event) =>
                    updateForm("biddingProcedure", event.target.value)
                  }
                >
                  <option value="simple">Einfaches Verfahren</option>
                  <option value="bid_range">Gebotsspanne</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Gebotsstufen</Form.Label>
                <Form.Select
                  value={form.bidLevels}
                  disabled={
                    !canEditSensitive ||
                    form.biddingProcedure === "bid_range"
                  }
                  onChange={(event) =>
                    updateForm("bidLevels", event.target.value)
                  }
                >
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={12}>
              <Form.Group>
                <Form.Label>Kommentar</Form.Label>
                <Form.Control
                  as={"textarea"}
                  rows={2}
                  value={form.comment}
                  onChange={(event) =>
                    updateForm("comment", event.target.value)
                  }
                />
              </Form.Group>
            </Col>
          </Row>

          {selectedProductType && (
            <>
              <h5 className={"mt-4"}>Werte je Anteilsgröße</h5>
              <Table size={"sm"} bordered>
                <thead>
                  <tr>
                    <th>Produkt</th>
                    <th>Richtwert (€/Monat)</th>
                    <th>Mindestbetrag (€/Monat)</th>
                    <th>Produktgröße *</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedProductType.products
                    .filter((product) => form.prices[product.id] !== undefined)
                    .map((product) => (
                      <tr key={product.id}>
                        <td>{product.name}</td>
                        <td>
                          <Form.Control
                            size={"sm"}
                            value={form.prices[product.id].referenceValue}
                            onChange={(event) =>
                              updatePrice(
                                product.id,
                                "referenceValue",
                                event.target.value,
                              )
                            }
                          />
                        </td>
                        <td>
                          <Form.Control
                            size={"sm"}
                            value={form.prices[product.id].minAmount}
                            onChange={(event) =>
                              updatePrice(
                                product.id,
                                "minAmount",
                                event.target.value,
                              )
                            }
                          />
                        </td>
                        <td>
                          <Form.Control
                            size={"sm"}
                            value={form.prices[product.id].size}
                            onChange={(event) =>
                              updatePrice(
                                product.id,
                                "size",
                                event.target.value,
                              )
                            }
                          />
                        </td>
                      </tr>
                    ))}
                </tbody>
              </Table>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant={"outline-dark"} onClick={closeModal}>
            Abbrechen
          </Button>
          <Button
            variant={"dark"}
            onClick={saveRound}
            disabled={!form.name || !form.endAt || hasInvalidSize}
          >
            Speichern
          </Button>
        </Modal.Footer>
      </Modal>

      <Card>
        <Card.Header>
          <strong>Vorhandene Runden</strong>
        </Card.Header>
        <Card.Body className={"p-0"}>
          {rounds.length === 0 ? (
            <Alert variant={"info"} className={"m-3"}>
              Noch keine Beitragsrunde angelegt.
            </Alert>
          ) : (
            <Table responsive hover className={"mb-0"}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Ende</th>
                  <th>Ziel (€/Jahr)</th>
                  <th>Gebote</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {rounds.map((round) => (
                  <tr key={round.id}>
                    <td>{round.name}</td>
                    <td>{round.status}</td>
                    <td>{new Date(round.endAt).toLocaleString("de-DE")}</td>
                    <td>{round.product?.targetAmountPerYear ?? "–"}</td>
                    <td>{round.hasBids ? "ja" : "nein"}</td>
                    <td>
                      <div className={"d-flex flex-wrap gap-1"}>
                        {round.status === "configuration" && (
                          <Button
                            size={"sm"}
                            variant={"dark"}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.biddingRoundsApiStartCreate({
                                    roundId: round.id,
                                  }),
                                "Beitragsrunde gestartet",
                              )
                            }
                          >
                            Starten
                          </Button>
                        )}
                        {round.status === "active" && (
                          <Button
                            size={"sm"}
                            variant={"dark"}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.biddingRoundsApiCloseCreate({
                                    roundId: round.id,
                                  }),
                                "Beitragsrunde geschlossen",
                              )
                            }
                          >
                            Schließen
                          </Button>
                        )}
                        {round.status === "closed" &&
                          !round.contractsCreatedAt && (
                            <Button
                              size={"sm"}
                              variant={"outline-dark"}
                              onClick={() =>
                                runAction(
                                  () =>
                                    api.biddingRoundsApiReopenCreate({
                                      roundId: round.id,
                                    }),
                                  "Beitragsrunde wieder geöffnet",
                                )
                              }
                            >
                              Öffnen
                            </Button>
                          )}
                        <Button
                          size={"sm"}
                          variant={"outline-dark"}
                          onClick={() => editRound(round)}
                        >
                          Bearbeiten
                        </Button>
                        <Button
                          size={"sm"}
                          variant={"outline-dark"}
                          href={`/bidding_rounds/admin/${round.id}/results`}
                        >
                          Auswertung
                        </Button>
                        <Button
                          size={"sm"}
                          variant={"outline-danger"}
                          onClick={() =>
                            runAction(
                              () =>
                                api.biddingRoundsApiDestroy({
                                  roundId: round.id,
                                }),
                              "Beitragsrunde gelöscht",
                            )
                          }
                        >
                          Löschen
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </Container>
  );
};

export default BiddingRoundConfig;
