import React, { useState, useEffect } from 'react';
import { YearWeekSelectorCard } from '../components/cards/YearWeekSelectorCard';
import { AllocationModal } from '../components/modals/AllocationModal';
import { InfoCircle } from 'react-bootstrap-icons';
import { BakeryApi } from '../../api-client';
import { useApi } from '../../hooks/useApi';
import type { BreadList } from '../../api-client/models';
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

interface DayConfig {
  day: number;
  label: string;
  dayNumber: number;
  breads: Record<string, boolean>;
}

const currentWeek = dayjs().isoWeek();
const currentYear = dayjs().year();

const DAY_LABELS: Record<number, string> = {
  0: 'Montag',
  1: 'Dienstag',
  2: 'Mittwoch',
  3: 'Donnerstag',
  4: 'Freitag',
  5: 'Samstag',
  6: 'Sonntag',
};

interface WeeklyPlanBreadsProps {
  csrfToken: string;
}

export const WeeklyPlanBreads: React.FC<WeeklyPlanBreadsProps> = ({ csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [year, setYear] = useState(currentYear);
  const [week, setWeek] = useState(currentWeek);
  const [allBreads, setAllBreads] = useState<BreadList[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [days, setDays] = useState<DayConfig[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState<{ day: number; label: string } | null>(null);

  const getDateForDay = (dayNumber: number): string => {
    const date = dayjs()
      .year(year)
      .isoWeek(week)
      .isoWeekday(dayNumber);
    return date.format('DD.MM.YYYY');
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (allBreads.length > 0 && days.length > 0) {
      loadDayConfigs();
    }
  }, [year, week, allBreads.length, days.length]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [breadsData, deliveryDaysData] = await Promise.all([
        bakeryApi.bakeryBreadsListList({}),
        bakeryApi.pickupLocationsApiDeliveryDaysRetrieve(),
      ]);

      setAllBreads(breadsData.filter((b: BreadList) => b.isActive !== false));

      const dayConfigs: DayConfig[] = deliveryDaysData.days.map((dayNumber: number) => ({
        day: dayNumber,
        label: DAY_LABELS[dayNumber] || `Tag ${dayNumber}`,
        dayNumber: dayNumber,
        breads: {},
      }));

      setDays(dayConfigs);
    } catch (error) {
      console.error('Failed to load initial data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const loadDayConfigs = async () => {
    setLoading(true);
    try {
      const updatedDays = await Promise.all(
        days.map(async (dayConfig) => {
          try {
            const response = await bakeryApi.bakeryAvailableBreadsForDeliveryRetrieve({
              year,
              week,
              day: dayConfig.day,
            } as any);

            const availableBreadIds = new Set((response as any).breads.map((b: any) => b.id));

            const breads: Record<string, boolean> = {};
            allBreads.forEach(bread => {
              breads[bread.id!] = availableBreadIds.has(bread.id!);
            });

            return { ...dayConfig, breads };
          } catch (error) {
            console.error(`Failed to load config for day ${dayConfig.day}:`, error);
            const breads: Record<string, boolean> = {};
            allBreads.forEach(bread => {
              breads[bread.id!] = false;
            });
            return { ...dayConfig, breads };
          }
        })
      );

      setDays(updatedDays);
    } catch (error) {
      console.error('Failed to load day configs:', error);
    } finally {
      setLoading(false);
    }
  };

// ...existing code...

const toggleBread = async (dayIndex: number, breadId: string) => {
  console.log("==================== TOGGLE BREAD DEBUG ====================");
  console.log("CSRF Token:", csrfToken);
  console.log("CSRF Token length:", csrfToken?.length);
  console.log("CSRF Token type:", typeof csrfToken);
  console.log("Day index:", dayIndex);
  console.log("Bread ID:", breadId);
  console.log("Day config:", days[dayIndex]);
  
  const newDays = [...days];
  const newState = !newDays[dayIndex].breads[breadId];
  newDays[dayIndex].breads[breadId] = newState;
  setDays(newDays);

  const payload = {
    year: year,
    week: week,
    day: newDays[dayIndex].day,
    breadId: breadId,
    isActive: newState,
  };
  
  console.log("Payload to send:", payload);

  setSaving(true);
  try {
    console.log("Calling bakeryApi.bakeryAvailableBreadsForDeliveryCreate...");
    
    const result = await bakeryApi.bakeryAvailableBreadsForDeliveryCreate({
      toggleBreadRequestRequest: payload
    });
    
    console.log("✅ SUCCESS! Result:", result);
    console.log("===========================================================");
  } catch (error) {
    console.error("❌ FAILED! Error details:");
    console.error("Error:", error);
    console.error("Error type:", typeof error);
    console.error("Error constructor:", error?.constructor?.name);
    
    if (error instanceof Response) {
      console.error("Response status:", error.status);
      console.error("Response statusText:", error.statusText);
      try {
        const errorText = await error.text();
        console.error("Response body:", errorText);
      } catch (e) {
        console.error("Could not read response body");
      }
    }
    
    console.log("===========================================================");
    
    newDays[dayIndex].breads[breadId] = !newState;
    setDays(newDays);
    alert('Fehler beim Speichern');
  } finally {
    setSaving(false);
  }
};

// ...existing code...

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
          />
        </div>
      </div>
      <div><h4>Liefertage</h4></div>

      <div className="row">
        {loading && days.length === 0 ? (
          <div className="col-12 text-center py-5">
            <div className="spinner-border" style={{ color: '#D4A574' }} />
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
                <div 
                  className="card-header d-flex justify-content-between align-items-center"
                  style={{ backgroundColor: '#D4A574', color: 'white' }}
                >
                  <div>
                    <h5 className="mb-0">{dayConfig.label}</h5>
                    <small className="opacity-75">{getDateForDay(dayConfig.dayNumber)}</small>
                  </div>
                  <small>KW {week}</small>
                </div>

                <div className="card-body" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                  {loading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border" style={{ color: '#D4A574' }} />
                    </div>
                  ) : allBreads.length === 0 ? (
                    <p className="text-muted text-center">Keine Brote verfügbar</p>
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
                                    width: '50px',
                                    height: '50px',
                                    objectFit: 'cover',
                                    borderRadius: '8px',
                                  }}
                                />
                              )}
                              <div>
                                <strong>{bread.name}</strong>
                                {bread.weight && (
                                  <div className="small text-muted">{Number(bread.weight).toFixed(0)} g</div>
                                )}
                              </div>
                            </div>

                            <div className="form-check form-switch">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                checked={isActive}
                                onChange={() => toggleBread(dayIndex, bread.id!)}
                                style={{
                                  backgroundColor: isActive ? '#8B6F47' : '',
                                  borderColor: isActive ? '#8B6F47' : '',
                                  cursor: 'pointer',
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
                  <button
                    className="btn w-100"
                    style={{ backgroundColor: '#8B6F47', color: 'white' }}
                    onClick={() => handleOpenModal(dayConfig.day, dayConfig.label)}
                    disabled={loading}
                  >
                    Abholorten Mengen zuweisen
                  </button>
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
          csrfToken={csrfToken}
        />
      )}
    </div>
  );
};