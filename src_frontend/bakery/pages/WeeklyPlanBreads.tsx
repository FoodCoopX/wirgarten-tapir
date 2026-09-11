import React, { useEffect, useRef, useState } from "react";
import { InfoCircle } from "react-bootstrap-icons";
import { BakeryApi } from "../../api-client";
import type { BreadList } from "../../api-client/models";
import TapirButton from "../../components/TapirButton";
import { useApi } from "../../hooks/useApi";
import { handleRequestError } from "../../utils/handleRequestError";
import { YearWeekSelectorCard } from "../components/cards";
import { AllocationModal, DailySettingsModal } from "../components/modals";
import "../styles/bakery_styles.css";
import {
  DAY_LABELS,
  currentIsoWeek,
  currentIsoYear,
  formatDeliveryDate,
} from "../utils/weekdays";

interface DayConfig {
  day: number;
  label: string;
  dayNumber: number;
  breads: Record<string, boolean>;
  // This day's request failed. Neither "all breads off" nor last week's values
  // may be shown as if they were this day's configuration - a switch rendered
  // from a guess is one toggleBread away from being written back as truth.
  failed?: boolean;
}

const currentWeek = currentIsoWeek();
const currentYear = currentIsoYear();

interface WeeklyPlanBreadsProps {
  csrfToken: string;
}

export const WeeklyPlanBreads: React.FC<WeeklyPlanBreadsProps> = ({
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [year, setYear] = useState(currentYear);
  const [week, setWeek] = useState(currentWeek);
  const [allBreads, setAllBreads] = useState<BreadList[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [days, setDays] = useState<DayConfig[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState<{
    day: number;
    label: string;
    activeBreads: BreadList[];
  } | null>(null);

  const getDateForDay = (dayNumber: number): string =>
    formatDeliveryDate(year, week, dayNumber);

  // The week currently on screen, as the other bakery pages track it.
  const selectionRef = useRef(`${year}/${week}`);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    selectionRef.current = `${year}/${week}`;
    if (allBreads.length > 0 && days.length > 0) {
      loadDayConfigs();
    }
  }, [year, week, allBreads.length, days.length]);

  const loadInitialData = () => {
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadsListList({}),
      bakeryApi.pickupLocationsApiDeliveryDaysRetrieve(),
    ])
      .then(([breadsData, deliveryDaysData]) => {
        setAllBreads(breadsData.filter((b: BreadList) => b.isActive !== false));

        const dayConfigs: DayConfig[] = deliveryDaysData.days.map(
          (dayNumber: number) => ({
            day: dayNumber,
            label: DAY_LABELS[dayNumber] || `Tag ${dayNumber}`,
            dayNumber: dayNumber,
            breads: {},
          }),
        );

        setDays(dayConfigs);
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Laden der Daten");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const loadDayConfigs = () => {
    const requestedFor = `${year}/${week}`;
    setLoading(true);
    Promise.all(
      days.map((dayConfig) =>
        bakeryApi
          .bakeryAvailableBreadsForDeliveryRetrieve({
            year,
            deliveryWeek: week,
            deliveryDay: dayConfig.day,
          })
          .then((response) => {
            const availableBreadIds = new Set(
              response.breads.map((bread) => bread.id),
            );

            const breads: Record<string, boolean> = {};
            allBreads.forEach((bread) => {
              breads[bread.id!] = availableBreadIds.has(bread.id!);
            });

            return { ...dayConfig, breads };
          })
          .catch((error) => {
            // Keep the failure local to its own day. Rethrowing would reject
            // the whole Promise.all and leave the entire grid showing the
            // previous week's switches under the new week's header.
            console.error(`Wochenplan: Tag ${dayConfig.day}`, error);
            return { ...dayConfig, breads: {}, failed: true };
          }),
      ),
    )
      .then((updatedDays) => {
        // The grid the user is now looking at, not the one they asked for.
        // Without this a slow earlier-week load repaints after they have moved
        // on - and toggleBread then writes the negation of that stale value
        // into the current week, so the race persists rather than just misleads.
        if (selectionRef.current !== requestedFor) return;
        setDays(updatedDays);
        if (updatedDays.some((day) => day.failed)) {
          handleRequestError(
            new Error(
              updatedDays
                .filter((day) => day.failed)
                .map((day) => day.label)
                .join(", "),
            ),
            "Wochenplan konnte für einzelne Tage nicht geladen werden",
          );
        }
      })
      .catch((error) => {
        if (selectionRef.current !== requestedFor) return;
        handleRequestError(error, "Fehler beim Laden des Wochenplans");
      })
      .finally(() => {
        if (selectionRef.current !== requestedFor) return;
        setLoading(false);
      });
  };

  // Every write goes through the updater form and touches exactly one
  // (day, bread) key, so a failed request reverts only its own switch and not
  // whatever else was toggled while it was in flight.
  const setBreadActive = (
    dayIndex: number,
    breadId: string,
    isActive: boolean,
  ) => {
    setDays((currentDays) =>
      currentDays.map((day, index) =>
        index === dayIndex
          ? { ...day, breads: { ...day.breads, [breadId]: isActive } }
          : day,
      ),
    );
  };

  const toggleBread = (dayIndex: number, breadId: string) => {
    const requestedFor = `${year}/${week}`;
    const currentState = days[dayIndex].breads[breadId] ?? false;
    const newState = !currentState;

    // Optimistic update
    setBreadActive(dayIndex, breadId, newState);

    setSaving(true);
    bakeryApi
      .bakeryAvailableBreadsForDeliveryCreate({
        toggleBreadRequestRequest: {
          year,
          deliveryWeek: week,
          deliveryDay: days[dayIndex].day,
          breadId,
          isActive: newState,
        },
      })
      .catch((error) => {
        // The revert is a write like any other: applying it after the user has
        // moved to another week would stamp this week's value onto that one.
        if (selectionRef.current !== requestedFor) return;
        setBreadActive(dayIndex, breadId, currentState);
        handleRequestError(error, "Fehler beim Speichern");
      })
      .finally(() => {
        if (selectionRef.current !== requestedFor) return;
        setSaving(false);
      });
  };

  const handleOpenModal = (day: number, label: string) => {
    // Get only active breads for this day
    const dayConfig = days.find((d) => d.day === day);
    const activeBreads = allBreads.filter(
      (bread) => dayConfig?.breads[bread.id!] === true,
    );

    setSelectedDay({ day, label, activeBreads });
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedDay(null);
  };

  return (
    <div className="container-fluid mt-4 px-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">Wochenplan Brote</h2>
        {saving && (
          <span className="badge bg-warning">
            <span className="spinner-border spinner-border-sm me-1" />
            Speichert...
          </span>
        )}
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <YearWeekSelectorCard
            selectedYear={year}
            selectedWeek={week}
            onYearChange={setYear}
            onWeekChange={setWeek}
          />
        </div>
      </div>
      <div>
        <h4>Liefertage</h4>
      </div>

      <div className="row">
        {loading && days.length === 0 ? (
          <div className="col-12 text-center py-5">
            <div className="spinner-border spinner-bakery-primary" />
            <p className="mt-2 text-muted">Lade Liefertage...</p>
          </div>
        ) : days.length === 0 ? (
          <div className="col-12 text-center py-5">
            <p className="text-muted">Keine Liefertage konfiguriert</p>
          </div>
        ) : (
          days.map((dayConfig, dayIndex) => (
            <div key={dayConfig.day} className="col-lg-4 mb-4">
              <div className="card h-100">
                <div className="card-header header-white-on-middle-brown d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="mb-0">{dayConfig.label}</h5>
                    <small className="opacity-75">
                      {getDateForDay(dayConfig.dayNumber)}
                    </small>
                  </div>
                  <small>KW {week}</small>
                </div>

                <div
                  className="card-body"
                  style={{ maxHeight: "600px", overflowY: "auto" }}
                >
                  {loading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-bakery-primary" />
                    </div>
                  ) : dayConfig.failed ? (
                    <p className="text-danger text-center">
                      Konnte nicht geladen werden.
                    </p>
                  ) : allBreads.length === 0 ? (
                    <p className="text-muted text-center">
                      Keine Brote verfügbar
                    </p>
                  ) : (
                    <div className="list-group list-group-flush">
                      {allBreads.map((bread) => {
                        const isActive = dayConfig.breads[bread.id!] ?? false;
                        return (
                          <div
                            key={bread.id}
                            className="list-group-item d-flex justify-content-between align-items-center border-0 px-0"
                          >
                            <div className="d-flex align-items-center flex-grow-1">
                              {bread.picture && (
                                <img
                                  src={bread.picture}
                                  alt={bread.name}
                                  className="me-3"
                                  style={{
                                    width: "50px",
                                    height: "50px",
                                    objectFit: "cover",
                                    borderRadius: "8px",
                                  }}
                                />
                              )}
                              <div>
                                <strong>{bread.name}</strong>
                                {bread.weight && (
                                  <div className="small text-muted">
                                    {Number(bread.weight).toFixed(0)} g
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="form-check form-switch">
                              <input
                                className={`form-check-input ${isActive ? "checkbox-bakery" : ""}`}
                                type="checkbox"
                                checked={isActive}
                                onChange={() =>
                                  toggleBread(dayIndex, bread.id!)
                                }
                                style={{
                                  cursor: "pointer",
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
                <div className="card-footer text-muted">
                  <small className="d-inline-flex align-items-center gap-1">
                    <InfoCircle size={14} />
                    Änderungen werden automatisch gespeichert
                  </small>
                </div>
                <div className="card-footer">
                  <TapirButton
                    variant=""
                    className="btn-bakery-brown w-100"
                    text="Abholorten max. Mengen zuweisen"
                    onClick={() =>
                      handleOpenModal(dayConfig.day, dayConfig.label)
                    }
                    disabled={loading}
                  />

                  <DailySettingsModal
                    year={year}
                    week={week}
                    day={dayConfig.day}
                    dayLabel={dayConfig.label}
                    activeBreads={allBreads.filter(
                      (bread) => dayConfig.breads[bread.id!] === true,
                    )}
                    csrfToken={csrfToken}
                  />
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {selectedDay && (
        <AllocationModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          year={year}
          week={week}
          day={selectedDay.day}
          dayLabel={selectedDay.label}
          activeBreads={selectedDay.activeBreads}
          csrfToken={csrfToken}
        />
      )}
    </div>
  );
};
