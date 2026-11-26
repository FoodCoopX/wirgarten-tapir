import React, { useEffect, useRef, useState } from "react";
import { InfoCircle } from "react-bootstrap-icons";
import { v4 as uuidv4 } from "uuid";
import { BakeryApi } from "../../api-client";
import type {
  BreadList,
  CopyWeekSettingsResponse,
} from "../../api-client/models";
import TapirButton from "../../components/TapirButton";
import TapirToastContainer from "../../components/TapirToastContainer";
import { useApi } from "../../hooks/useApi";
import { ToastData } from "../../types/ToastData";
import { addToast } from "../../utils/addToast";
import { handleRequestError } from "../../utils/handleRequestError";
import {
  CopyWeekSettingsSelector,
  YearWeekSelectorCard,
} from "../components/cards";
import {
  DailySettingsModal,
  DirectOrderLimitsModal,
} from "../components/modals";
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
  failed?: boolean;
  // Its breads can no longer be switched on or off.
  isOver?: boolean;
}

const currentWeek = currentIsoWeek();
const currentYear = currentIsoYear();

const choicesText = (count: number) =>
  `${count} ${count === 1 ? "Brotwahl" : "Brotwahlen"}`;

// After the members' deadline they cannot choose again; the solver then
// shares out breads to their slots, by their preferences where it can.
const clearedChoicesNote = (count: number) =>
  `${choicesText(count)} ${count === 1 ? "wurde" : "wurden"} zurückgesetzt. Ist die Wahlfrist schon vorbei, bekommen diese Mitglieder ein Brot möglichst nach ihren Vorlieben. Einen schon berechneten Backplan bitte neu berechnen.`;

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
  // A count, not a flag: saves of a week switched away from still finish.
  const [pendingSaves, setPendingSaves] = useState(0);
  const saving = pendingSaves > 0;
  // The switches with a request on the way: a second click would ask again
  // or overtake the first request.
  const [busySwitches, setBusySwitches] = useState<Set<string>>(new Set());
  const [days, setDays] = useState<DayConfig[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState<{
    day: number;
    label: string;
  } | null>(null);
  const [toastDatas, setToastDatas] = useState<ToastData[]>([]);

  const getDateForDay = (dayNumber: number): string =>
    formatDeliveryDate(year, week, dayNumber);

  const selectionRef = useRef(`${year}/${week}`);

  const switchKey = (day: number, breadId: string) =>
    `${year}/${week}/${day}/${breadId}`;

  const setSwitchBusy = (key: string, busy: boolean) => {
    setBusySwitches((current) => {
      const next = new Set(current);
      if (busy) {
        next.add(key);
      } else {
        next.delete(key);
      }
      return next;
    });
  };

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
      bakeryApi.bakeryApiDeliveryDaysRetrieve(),
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
        handleRequestError(error, "Fehler beim Laden der Daten", setToastDatas);
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

            return {
              ...dayConfig,
              breads,
              isOver: response.deliveryDayIsOver,
            };
          })
          .catch((error) => {
            console.error(`Wochenplan: Tag ${dayConfig.day}`, error);
            return { ...dayConfig, breads: {}, failed: true };
          }),
      ),
    )
      .then((updatedDays) => {
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
            setToastDatas,
          );
        }
      })
      .catch((error) => {
        if (selectionRef.current !== requestedFor) return;
        handleRequestError(
          error,
          "Fehler beim Laden des Wochenplans",
          setToastDatas,
        );
      })
      .finally(() => {
        if (selectionRef.current !== requestedFor) return;
        setLoading(false);
      });
  };

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
    const key = switchKey(days[dayIndex].day, breadId);
    if (busySwitches.has(key)) return;
    setSwitchBusy(key, true);

    const currentState = days[dayIndex].breads[breadId] ?? false;
    if (!currentState) {
      saveBreadActive(dayIndex, breadId, true).finally(() =>
        setSwitchBusy(key, false),
      );
      return;
    }

    // Switching a bread off clears the members' choices of it for that day,
    // so count them first and ask.
    const requestedFor = `${year}/${week}`;
    setPendingSaves((count) => count + 1);
    bakeryApi
      .bakeryAvailableBreadsForDeliveryCreate({
        toggleBreadRequestRequest: {
          year,
          deliveryWeek: week,
          deliveryDay: days[dayIndex].day,
          breadId,
          isActive: false,
          dryRun: true,
        },
      })
      .then((response) => {
        if (selectionRef.current !== requestedFor) return;
        const count = response.clearedChoices ?? 0;
        if (
          count > 0 &&
          !confirm(
            `${choicesText(count)} von Mitgliedern für diesen Tag ${count === 1 ? "wird" : "werden"} zurückgesetzt und beim Wiedereinschalten nicht wiederhergestellt. Trotzdem abschalten?`,
          )
        ) {
          return;
        }
        return saveBreadActive(dayIndex, breadId, false);
      })
      .catch((error) => {
        handleRequestError(
          error,
          "Fehler beim Prüfen der Brotwahlen",
          setToastDatas,
        );
      })
      .finally(() => {
        setPendingSaves((count) => count - 1);
        setSwitchBusy(key, false);
      });
  };

  const saveBreadActive = (
    dayIndex: number,
    breadId: string,
    newState: boolean,
  ): Promise<void> => {
    const requestedFor = `${year}/${week}`;
    const currentState = !newState;
    const dayAndWeek = `${days[dayIndex].label}, KW ${week}/${year}`;

    setBreadActive(dayIndex, breadId, newState);

    setPendingSaves((count) => count + 1);
    return bakeryApi
      .bakeryAvailableBreadsForDeliveryCreate({
        toggleBreadRequestRequest: {
          year,
          deliveryWeek: week,
          deliveryDay: days[dayIndex].day,
          breadId,
          isActive: newState,
        },
      })
      .then((response) => {
        if (response.clearedChoices) {
          addToast(
            {
              title: `Brotwahlen zurückgesetzt (${dayAndWeek})`,
              message: clearedChoicesNote(response.clearedChoices),
              variant: "warning",
              id: uuidv4(),
            },
            setToastDatas,
          );
        }
      })
      .catch((error) => {
        // After a switch to another week the shown switches belong to that
        // week, so only roll back on the week the save was for.
        if (selectionRef.current === requestedFor) {
          setBreadActive(dayIndex, breadId, currentState);
        }
        handleRequestError(
          error,
          `Fehler beim Speichern (${dayAndWeek})`,
          setToastDatas,
        );
      })
      .finally(() => {
        setPendingSaves((count) => count - 1);
      });
  };

  const handleWeekSettingsCopied = (
    result: CopyWeekSettingsResponse,
    target: { year: number; week: number },
  ) => {
    addToast(
      {
        title: `Einstellungen in KW ${target.week}/${target.year} übernommen`,
        message:
          result.clearedChoices > 0
            ? clearedChoicesNote(result.clearedChoices)
            : "Einen schon berechneten Backplan dieser Woche bitte neu berechnen.",
        variant: result.clearedChoices > 0 ? "warning" : "success",
        id: uuidv4(),
      },
      setToastDatas,
    );
    if (selectionRef.current === `${target.year}/${target.week}`) {
      loadDayConfigs();
    }
  };

  const handleOpenModal = (day: number, label: string) => {
    setSelectedDay({ day, label });
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
          >
            <CopyWeekSettingsSelector
              year={year}
              week={week}
              csrfToken={csrfToken}
              disabled={loading || saving}
              onCopied={handleWeekSettingsCopied}
              setToastDatas={setToastDatas}
            />
          </YearWeekSelectorCard>
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
                        const locked =
                          dayConfig.isOver ||
                          busySwitches.has(switchKey(dayConfig.day, bread.id!));
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
                                disabled={locked}
                                onChange={() =>
                                  toggleBread(dayIndex, bread.id!)
                                }
                                style={{
                                  cursor: locked ? "not-allowed" : "pointer",
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
                    {dayConfig.isOver
                      ? "Liefertag ist vorbei: Brote lassen sich nicht mehr umschalten"
                      : "Änderungen werden automatisch gespeichert"}
                  </small>
                </div>
                <div className="card-footer">
                  <TapirButton
                    variant=""
                    className="btn-bakery-brown w-100"
                    text="Brotsorten max. Bestellmengen zuweisen"
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
        <DirectOrderLimitsModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          year={year}
          week={week}
          day={selectedDay.day}
          dayLabel={selectedDay.label}
          csrfToken={csrfToken}
          setToastDatas={setToastDatas}
        />
      )}
      <TapirToastContainer
        toastDatas={toastDatas}
        setToastDatas={setToastDatas}
      />
    </div>
  );
};
