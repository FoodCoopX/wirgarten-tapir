import React, { useEffect, useState } from "react";
import { Form, Modal, Table } from "react-bootstrap";
import { ExclamationTriangle, InfoCircle } from "react-bootstrap-icons";
import { BakeryApi } from "../../../api-client";
import type {
  BreadDirectOrderLimit,
  GroupDirectOrderLimit,
  TotalCapacitySourceEnum,
} from "../../../api-client/models";
import TapirButton from "../../../components/TapirButton";
import { useApi } from "../../../hooks/useApi";
import { ToastData } from "../../../types/ToastData";
import { handleRequestError } from "../../../utils/handleRequestError";
import "../../styles/bakery_styles.css";

interface DirectOrderLimitsModalProps {
  isOpen: boolean;
  onClose: () => void;
  year: number;
  week: number;
  day: number;
  dayLabel: string;
  csrfToken: string;
  setToastDatas: React.Dispatch<React.SetStateAction<ToastData[]>>;
}

const CAPACITY_SOURCE_LABELS: Record<TotalCapacitySourceEnum, string> = {
  fixed: "Fixe Stück des Tages",
  day_max: "Max. Stück des Tages",
  group_max: "Max. Stück der Gruppe",
  bread_max: "Max. Stück des Brots",
};

// The same rounding as DirectOrderLimitService.compute_limit: down to whole
// loaves, so the limit is never exceeded.
function computeLimit(
  percent: number,
  capacity: number | null,
  minRemaining: number,
): number | null {
  if (capacity == null) return null;
  return Math.floor((percent * Math.max(capacity - minRemaining, 0)) / 100);
}

export const DirectOrderLimitsModal: React.FC<DirectOrderLimitsModalProps> = ({
  isOpen,
  onClose,
  year,
  week,
  day,
  dayLabel,
  csrfToken,
  setToastDatas,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadDirectOrderLimit[]>([]);
  const [groups, setGroups] = useState<GroupDirectOrderLimit[]>([]);
  const [percents, setPercents] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, year, week, day]);

  function loadData() {
    setLoading(true);
    setLoadFailed(false);
    bakeryApi
      .bakeryApiDirectOrderLimitsRetrieve({
        year,
        deliveryWeek: week,
        deliveryDay: day,
      })
      .then((response) => {
        setBreads(response.breads);
        setGroups(response.groups);
        setPercents(
          Object.fromEntries(
            response.breads.map((b) => [b.breadId, b.percent]),
          ),
        );
      })
      .catch((error) => {
        setLoadFailed(true);
        handleRequestError(
          error,
          "Fehler beim Laden der Bestellmengen",
          setToastDatas,
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    // Only in a field: on a button, Enter presses that button.
    if (
      e.key === "Enter" &&
      e.target instanceof HTMLInputElement &&
      !saving &&
      !loading &&
      !loadFailed
    ) {
      e.preventDefault();
      handleSaveAndClose();
    }
  }

  function handleSaveAndClose() {
    // The bread's own value is the default, so a day equal to it needs no
    // override of its own.
    const updates = breads
      .filter((b) => percents[b.breadId] !== b.percent)
      .map((b) => ({
        bread: b.breadId,
        maxDirectOrderPercent:
          percents[b.breadId] === b.defaultPercent ? null : percents[b.breadId],
      }));

    if (updates.length === 0) {
      onClose();
      return;
    }

    setSaving(true);
    bakeryApi
      .bakeryBreadSpecificsBulkUpdateCreate({
        breadSpecificsPerDeliveryDayBulkUpdateRequest: {
          year,
          deliveryWeek: week,
          deliveryDay: day,
          updates,
        },
      })
      .then(() => {
        onClose();
      })
      .catch((error) => {
        handleRequestError(
          error,
          "Fehler beim Speichern der Bestellmengen",
          setToastDatas,
        );
      })
      .finally(() => {
        setSaving(false);
      });
  }

  // bakeable is the limit at 100 %: beyond it the day's plan cannot be
  // computed at all, while beyond a lower percentage only new orders stop.
  // capacityName says what bounds the capacity, to raise it.
  function renderOrderedWarning(
    ordered: number,
    limit: number | null,
    bakeable: number | null,
    capacityName: string,
  ) {
    if (bakeable != null && ordered > bakeable) {
      return (
        <small className="text-danger d-flex align-items-center gap-1">
          <ExclamationTriangle size={12} />
          Mehr bestellt als gebacken werden kann: so lässt sich kein Backplan
          berechnen. {capacityName} erhöhen oder Brotwahlen zurücksetzen.
        </small>
      );
    }
    if (limit == null || ordered <= limit) return null;
    return (
      <small className="text-warning-emphasis d-flex align-items-center gap-1">
        <ExclamationTriangle size={12} />
        Mehr bestellt als erlaubt: bestehende Bestellungen bleiben, neue werden
        abgelehnt.
      </small>
    );
  }

  function renderBreadRow(bread: BreadDirectOrderLimit) {
    const percent = percents[bread.breadId] ?? bread.percent;
    const limit = computeLimit(
      percent,
      bread.totalCapacity,
      bread.minRemaining,
    );
    const bakeable = computeLimit(100, bread.totalCapacity, bread.minRemaining);
    const unlimited = bread.totalCapacity == null;

    return (
      <tr key={bread.breadId}>
        <td className="fw-bold align-middle">
          {bread.breadName}
          {bread.groupName && (
            <small className="text-muted d-block fw-normal">
              Gruppe {bread.groupName}
            </small>
          )}
        </td>
        <td className="text-center align-middle">
          {unlimited ? (
            "–"
          ) : (
            <>
              {bread.totalCapacity}
              <small className="text-muted d-block">
                {CAPACITY_SOURCE_LABELS[bread.totalCapacitySource!]}
              </small>
            </>
          )}
        </td>
        <td className="text-center align-middle">{bread.minRemaining}</td>
        <td className="align-middle" style={{ minWidth: "220px" }}>
          {unlimited ? (
            <small className="text-muted">
              Unbegrenzt bestellbar: für eine Grenze Max. Stück beim Brot oder
              in den Tageseinstellungen setzen
            </small>
          ) : (
            <>
              <div className="d-flex align-items-center gap-2">
                <Form.Range
                  aria-label={`Max. direkt bestellbar (%): ${bread.breadName}`}
                  min={0}
                  max={100}
                  step={1}
                  value={percent}
                  onChange={(e) =>
                    setPercents((prev) => ({
                      ...prev,
                      [bread.breadId]: Number(e.target.value),
                    }))
                  }
                />
                <span style={{ minWidth: "3.5em" }} className="text-end">
                  {percent} %
                </span>
              </div>
              <small className="text-muted">
                Standard des Brots: {bread.defaultPercent} %
              </small>
            </>
          )}
        </td>
        <td className="text-center align-middle fw-bold">
          {unlimited ? "–" : limit}
        </td>
        <td className="text-center align-middle">
          {bread.ordered}
          {!unlimited &&
            renderOrderedWarning(
              bread.ordered,
              limit,
              bakeable,
              CAPACITY_SOURCE_LABELS[bread.totalCapacitySource!],
            )}
        </td>
      </tr>
    );
  }

  function renderGroup(group: GroupDirectOrderLimit) {
    // The group's percentage is the highest of its breads', see
    // DirectOrderLimitService.
    const percent = Math.max(
      ...group.breadIds.map(
        (id) =>
          percents[id] ?? breads.find((b) => b.breadId === id)?.percent ?? 0,
      ),
    );
    const heldBack = group.minRemaining + group.openMinPieces;
    const limit = computeLimit(percent, group.totalCapacity, heldBack);
    // The percentage applies to what is left after the deductions.
    const bakeable = computeLimit(100, group.totalCapacity, heldBack);
    const deductions = [
      group.fixedPieces > 0 ? `${group.fixedPieces} Fixe Stück` : null,
      `${group.minRemaining} Min. Rest`,
      group.openMinPieces > 0
        ? `${group.openMinPieces} noch nicht bestellte Min. Stück`
        : null,
    ].filter((text): text is string => text !== null);
    const deductionText =
      deductions.length > 1
        ? `${deductions.slice(0, -1).join(", ")} und ${deductions.at(-1)}`
        : deductions[0];

    return (
      <li key={group.groupId}>
        <strong>Gruppe {group.groupName}</strong> zusammen
        {group.fixedPieces > 0 && " (ohne Brote mit „Fixe Stück“)"}:{" "}
        {limit == null ? (
          "unbegrenzt (kein Max. Stück bei den Broten der Gruppe)"
        ) : (
          <>
            höchstens <strong>{limit}</strong> ({percent} % von {bakeable}:{" "}
            {group.maxPieces} abzüglich {deductionText}), bereits bestellt{" "}
            {group.ordered}
          </>
        )}
        {renderOrderedWarning(
          group.ordered,
          limit,
          bakeable,
          "Max. Stück der Brote",
        )}
      </li>
    );
  }

  function renderModalBodyContent() {
    if (loading) {
      return (
        <div className="text-center py-5">
          <div className="spinner-border spinner-bakery-primary" />
          <p className="mt-2 text-muted">Lade Daten...</p>
        </div>
      );
    }

    if (loadFailed) {
      return (
        <div
          className="alert alert-danger d-flex align-items-center"
          role="alert"
        >
          <ExclamationTriangle size={20} className="me-2" />
          Die Bestellmengen konnten nicht geladen werden.
        </div>
      );
    }

    if (breads.length === 0) {
      return (
        <div
          className="alert alert-info d-flex align-items-center"
          role="alert"
        >
          <InfoCircle size={20} className="me-2" />
          Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im
          Wochenplan.
        </div>
      );
    }

    return (
      <>
        <p className="text-muted small">
          Welcher Anteil der Gesamtkapazität (abzüglich Min. Rest) von
          Mitgliedern direkt bestellt werden kann, über alle Abholorte dieses
          Tages zusammen. Ohne Einstellung hier gilt der Standard des Brots.
        </p>
        <Table responsive bordered hover className="mb-3">
          <thead className="table-header-bakery">
            <tr>
              <th>Brot</th>
              <th className="text-center">Gesamtkapazität</th>
              <th className="text-center">Min. Rest</th>
              <th className="text-center">Max. direkt bestellbar (%)</th>
              <th className="text-center">Max. direkt bestellbar (Stück)</th>
              <th className="text-center">Bereits bestellt</th>
            </tr>
          </thead>
          <tbody>{breads.map(renderBreadRow)}</tbody>
        </Table>
        {groups.length > 0 && (
          <ul className="small mb-0">{groups.map(renderGroup)}</ul>
        )}
      </>
    );
  }

  return (
    <Modal
      show={isOpen}
      // Closing while saving would drop the edits if the save then fails.
      onHide={() => {
        if (!saving) onClose();
      }}
      backdrop={saving ? "static" : true}
      keyboard={!saving}
      size="xl"
      centered
      scrollable
      onKeyDown={handleKeyDown}
    >
      <Modal.Header closeButton className="header-white-on-middle-brown">
        <Modal.Title>
          <h5 className="mb-0">
            Max. Bestellmengen — {dayLabel}, KW {week}/{year}
          </h5>
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="p-3">{renderModalBodyContent()}</Modal.Body>

      <Modal.Footer>
        <TapirButton
          variant="outline-secondary"
          text="Abbrechen"
          icon="close"
          onClick={onClose}
          disabled={saving}
          size="sm"
        />
        <TapirButton
          variant=""
          className="dark-brown-button"
          text="Speichern & Schließen"
          icon="save"
          onClick={handleSaveAndClose}
          disabled={saving || loading || loadFailed}
          loading={saving}
          size="sm"
        />
      </Modal.Footer>
    </Modal>
  );
};
