import React, { useState, useEffect, useCallback } from 'react';
import { YearWeekSelectorCard } from '../components/cards/YearWeekSelectorCard';
import { BakeryApi, PickupLocationsApi } from '../../api-client';
import { useApi } from '../../hooks/useApi';
import type { AbhollisteEntry, BreadDelivery, PickupLocation } from '../../api-client/models';
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";
import { RunSolverCard } from '../components/cards/RunSolverCard';

dayjs.extend(isoWeek);

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

interface ReportsProps {
  csrfToken: string;
}

export const Reports: React.FC<ReportsProps> = ({ csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const pickupLocationsApi = useApi(PickupLocationsApi, csrfToken);

  const [year, setYear] = useState(currentYear);
  const [week, setWeek] = useState(currentWeek);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [deliveryDays, setDeliveryDays] = useState<number[]>([]);
  const [allPickupLocations, setAllPickupLocations] = useState<PickupLocation[]>([]);

  const [breadSummaryByDay, setBreadSummaryByDay] = useState<Record<number, Record<string, number>>>({});
  const [distributionByDay, setDistributionByDay] = useState<Record<number, Record<string, Record<string, number>>>>({});

  const [selectedPickupLocationByDay, setSelectedPickupLocationByDay] = useState<Record<number, string>>({});
  const [abhollisteByDay, setAbhollisteByDay] = useState<Record<number, AbhollisteEntry[]>>({});
  const [abhollisteLoadingByDay, setAbhollisteLoadingByDay] = useState<Record<number, boolean>>({});
  const [checkedByDay, setCheckedByDay] = useState<Record<number, Record<string, boolean>>>({});

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadBreadDeliveries();
  }, [year, week]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [deliveryDaysData, pickupLocations] = await Promise.all([
        bakeryApi.pickupLocationsApiDeliveryDaysRetrieve(),
        pickupLocationsApi.pickupLocationsPickupLocationsList(),
      ]);
      setDeliveryDays(deliveryDaysData.days);
      setAllPickupLocations(pickupLocations);
    } catch (error) {
      console.error('Failed to load initial data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const getPickupLocationsForDay = (day: number): PickupLocation[] =>
    allPickupLocations.filter(pl => pl.deliveryDay === day);

  console.log("allPickupLocations", allPickupLocations);

  const getDateForDay = (day: number): string =>
    dayjs().year(year).isoWeek(week).isoWeekday(day).format('DD.MM.YYYY');

  const loadBreadDeliveries = async () => {
    try {
      const data = await bakeryApi.bakeryBreadDeliveriesList({ year, deliveryWeek: week });

      const summary: Record<number, Record<string, number>> = {};
      const dist: Record<number, Record<string, Record<string, number>>> = {};

      data.forEach(({ deliveryDay, breadName: bn, pickupLocationName: pln }) => {
        if (deliveryDay == null) return;
        const bread_name = bn || 'Unbekannt';
        const location = pln || 'Unbekannt';

        summary[deliveryDay] ??= {};
        summary[deliveryDay][bread_name] = (summary[deliveryDay][bread_name] || 0) + 1;

        dist[deliveryDay] ??= {};
        dist[deliveryDay][location] ??= {};
        dist[deliveryDay][location][bread_name] = (dist[deliveryDay][location][bread_name] || 0) + 1;
      });

      setBreadSummaryByDay(summary);
      setDistributionByDay(dist);
    } catch (error) {
      console.error('Failed to load bread deliveries:', error);
    }
  };

  const loadAbholliste = useCallback(async (day: number, pickupLocationId: string) => {
    if (!pickupLocationId) {
      setAbhollisteByDay(prev => ({ ...prev, [day]: [] }));
      return;
    }
    setAbhollisteLoadingByDay(prev => ({ ...prev, [day]: true }));
    try {
      const data = await bakeryApi.bakeryAbhollisteList({ year, week, pickupLocationId });
      setAbhollisteByDay(prev => ({ ...prev, [day]: data }));
      setCheckedByDay(prev => ({ ...prev, [day]: {} }));
    } catch (error) {
      console.error('Failed to load Abholliste:', error);
      setAbhollisteByDay(prev => ({ ...prev, [day]: [] }));
    } finally {
      setAbhollisteLoadingByDay(prev => ({ ...prev, [day]: false }));
    }
  }, [year, week]);

  // Reload abholliste when year/week changes
  useEffect(() => {
    Object.entries(selectedPickupLocationByDay).forEach(([dayStr, locationId]) => {
      if (locationId) loadAbholliste(parseInt(dayStr), locationId);
    });
  }, [year, week, loadAbholliste]);

  const handlePickupLocationChange = (day: number, pickupLocationId: string) => {
    setSelectedPickupLocationByDay(prev => ({ ...prev, [day]: pickupLocationId }));
    loadAbholliste(day, pickupLocationId);
  };

  const handleCheckToggle = (day: number, memberId: string) => {
    setCheckedByDay(prev => ({
      ...prev,
      [day]: { ...(prev[day] || {}), [memberId]: !prev[day]?.[memberId] },
    }));
  };

  const handleDownload = async (reportType: string, day: number) => {
    setDownloading(`${reportType}-${day}`);
    try {
      alert(`${reportType} für KW ${week}/${year} wird heruntergeladen...`);
    } finally {
      setDownloading(null);
    }
  };

  const handleEmail = async (reportType: string, day: number) => {
    setDownloading(`${reportType}-${day}`);
    try {
      alert(`${reportType} für KW ${week}/${year} wird per E-Mail versendet...`);
    } finally {
      setDownloading(null);
    }
  };

  const ActionButtons = ({ reportType, day, label }: { reportType: string; day: number; label: string }) => {
    const key = `${reportType}-${day}`;
    return (
      <div className="d-grid gap-2">
        <button
          className="btn btn-sm"
          style={{ backgroundColor: '#8B6F47', color: 'white' }}
          onClick={() => handleDownload(reportType, day)}
          disabled={downloading === key}
        >
          <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>download</span>
          {label} als PDF herunterladen
        </button>
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() => handleEmail(reportType, day)}
          disabled={downloading === key}
        >
          <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>email</span>
          {label} per E-Mail senden
        </button>
      </div>
    );
  };

  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Berichte & Listen</h2>

      <div className="card mb-4">
        <div className="card-body">
          <YearWeekSelectorCard
            selectedYear={year} selectedWeek={week}
            onYearChange={setYear} onWeekChange={setWeek}
          />
        </div>
      </div>
     

      <div className="row">
        {loading ? (
          <div className="col-12 text-center py-5">
            <div className="spinner-border" style={{ color: '#D4A574' }} />
            <p className="mt-2 text-muted">Lade Liefertage...</p>
          </div>
        ) : deliveryDays.length === 0 ? (
          <div className="col-12 text-center py-5">
            <p className="text-muted">Keine Liefertage konfiguriert</p>
          </div>
        ) : (
          deliveryDays.map((day) => {
            const daySummary = breadSummaryByDay[day] || {};
            const totalBreads = Object.values(daySummary).reduce((s, c) => s + c, 0);
            const dayDistribution = distributionByDay[day] || {};

            const distBreadNames = [...new Set(
              Object.values(dayDistribution).flatMap(loc => Object.keys(loc))
            )].sort();

            const dayPickupLocations = getPickupLocationsForDay(day);
            const selectedLocation = selectedPickupLocationByDay[day] || '';
            const abholliste = abhollisteByDay[day] || [];
            const abhollisteLoading = abhollisteLoadingByDay[day] || false;
            const dayChecked = checkedByDay[day] || {};

            const abhollisteBreadNames = [...new Set(
              abholliste.flatMap(e => e.breads.map(b => b.bread_name).filter(Boolean) as string[])
            )].sort();



            return (
              <div key={day} className="col-lg-4 mb-4">
                <div className="card h-100">
                  <div className="card-header" style={{ backgroundColor: '#D4A574', color: 'white' }}>
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        <h5 className="mb-0">{DAY_LABELS[day] || `Tag ${day}`}</h5>
                        <small className="opacity-75">{getDateForDay(day)}</small>
                      </div>
                      <small>KW {week}</small>
                    </div>
                     <div className="mb-4">
                      <RunSolverCard
                        year={year}
                        deliveryWeek={week}
                        deliveryDay={day}
                        csrfToken={csrfToken}
                      />
                    </div>
                  </div>

                  <div className="card-body">
                    {/* Backliste */}
                    <div className="mb-4">
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>bakery_dining</span>
                        Backliste
                      </h6>
                      <p className="text-muted small mb-2">Liste aller zu backenden Brote</p>

                      {Object.keys(daySummary).length > 0 && (
                        <div className="table-responsive mb-3">
                          <table className="table table-sm table-striped">
                            <thead style={{ backgroundColor: '#F5E6D3', fontSize: '0.85rem' }}>
                              <tr><th>Brotsorte</th><th className="text-end">Anzahl</th></tr>
                            </thead>
                            <tbody style={{ fontSize: '0.9rem' }}>
                              {Object.entries(daySummary).sort(([a], [b]) => a.localeCompare(b)).map(([name, count]) => (
                                <tr key={name}>
                                  <td>{name}</td>
                                  <td className="text-end"><strong style={{ color: '#8B4513' }}>{count}</strong></td>
                                </tr>
                              ))}
                              <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                <td>Gesamt</td><td className="text-end">{totalBreads}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}
                      <ActionButtons reportType="backliste" day={day} label="Backliste" />
                    </div>

                    <hr />

                    {/* Verteilliste */}
                    <div className="mb-4">
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>warehouse</span>
                        Verteilliste
                      </h6>
                      <p className="text-muted small mb-2">Brote pro Abholstation</p>

                      {Object.keys(dayDistribution).length > 0 && (
                        <div className="table-responsive mb-3">
                          <table className="table table-sm table-bordered" style={{ fontSize: '0.8rem' }}>
                            <thead style={{ backgroundColor: '#F5E6D3' }}>
                              <tr>
                                <th>Station</th>
                                {distBreadNames.map(name => (
                                  <th key={name} className="text-center" style={{
                                    writingMode: 'vertical-rl', transform: 'rotate(180deg)',
                                    minWidth: '30px', maxWidth: '30px', padding: '8px 4px', fontSize: '0.75rem',
                                  }}>{name}</th>
                                ))}
                                <th className="text-center">Σ</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(dayDistribution).sort(([a], [b]) => a.localeCompare(b)).map(([loc, breads]) => {
                                const total = Object.values(breads).reduce((s, c) => s + c, 0);
                                return (
                                  <tr key={loc}>
                                    <td style={{ fontSize: '0.75rem' }}>{loc}</td>
                                    {distBreadNames.map(name => (
                                      <td key={name} className="text-center">{breads[name] || '-'}</td>
                                    ))}
                                    <td className="text-center" style={{ fontWeight: 'bold', backgroundColor: '#F5E6D3' }}>{total}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                      <ActionButtons reportType="verteilungsliste" day={day} label="Verteilliste" />
                    </div>

                    <hr />

                    {/* Abholliste */}
                    <div>
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>local_shipping</span>
                        Abholliste
                      </h6>
                      <p className="text-muted small mb-2">Brote pro Mitglied am Abholort</p>

                      <div className="mb-3">
                        <select
                          className="form-select form-select-sm"
                          value={selectedLocation}
                          onChange={(e) => handlePickupLocationChange(day, e.target.value)}
                        >
                          <option value="">Abholort auswählen...</option>
                          {dayPickupLocations.map(pl => (
                            <option key={pl.id} value={pl.id}>{pl.name}</option>
                          ))}
                        </select>
                      </div>

                      {abhollisteLoading ? (
                        <div className="text-center py-3">
                          <div className="spinner-border spinner-border-sm" style={{ color: '#D4A574' }} />
                          <p className="mt-1 text-muted small">Lade Abholliste...</p>
                        </div>
                      ) : selectedLocation && abholliste.length > 0 ? (
                        <div className="table-responsive mb-3">
                          <table className="table table-sm table-bordered" style={{ fontSize: '0.8rem' }}>
                            <thead style={{ backgroundColor: '#F5E6D3' }}>
                              <tr>
                                <th className="text-center" style={{ width: '30px' }}>#</th>
                                <th>Name</th>
                                <th className="text-center" style={{ width: '40px' }}>Σ</th>
                                <th className="text-center" style={{ width: '30px' }}>
                                  <span className="material-icons" style={{ fontSize: '14px' }}>check</span>
                                </th>
                                {abhollisteBreadNames.map(name => (
                                  <th key={name} className="text-center" style={{
                                    writingMode: 'vertical-rl', transform: 'rotate(180deg)',
                                    minWidth: '28px', maxWidth: '28px', padding: '8px 2px', fontSize: '0.7rem',
                                  }}>{name}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {abholliste.map((entry, index) => {
                                const breadCounts: Record<string, number> = {};
                                entry.breads.forEach(b => {
                                  if (b.bread_name) breadCounts[b.bread_name] = (breadCounts[b.bread_name] || 0) + 1;
                                });
                                const isChecked = dayChecked[entry.memberId] || false;

                                return (
                                  <tr key={entry.memberId} style={{
                                    backgroundColor: isChecked ? '#d4edda' : undefined,
                                    textDecoration: isChecked ? 'line-through' : undefined,
                                    opacity: isChecked ? 0.7 : 1,
                                  }}>
                                    <td className="text-center text-muted">{index + 1}</td>
                                    <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{entry.displayName}</td>
                                    <td className="text-center">
                                      <strong style={{ color: '#8B4513' }}>{entry.totalBreads}</strong>
                                    </td>
                                    <td className="text-center">
                                      <input
                                        type="checkbox" className="form-check-input"
                                        checked={isChecked}
                                        onChange={() => handleCheckToggle(day, entry.memberId)}
                                        style={{ cursor: 'pointer' }}
                                      />
                                    </td>
                                    {abhollisteBreadNames.map(name => (
                                      <td key={name} className="text-center">{breadCounts[name] || '-'}</td>
                                    ))}
                                  </tr>
                                );
                              })}
                              <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                <td />
                                <td>Gesamt</td>
                                <td className="text-center">
                                  {abholliste.reduce((sum, e) => sum + e.totalBreads, 0)}
                                </td>
                                <td className="text-center">
                                  {Object.values(dayChecked).filter(Boolean).length}/{abholliste.length}
                                </td>
                                {abhollisteBreadNames.map(name => {
                                  const total = abholliste.reduce((sum, e) =>
                                    sum + e.breads.filter(b => b.bread_name === name).length, 0);
                                  return <td key={name} className="text-center">{total}</td>;
                                })}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      ) : selectedLocation ? (
                        <p className="text-muted small text-center py-2">
                          Keine Brotbestellungen für diesen Abholort.
                        </p>
                      ) : null}

                      <ActionButtons reportType="abholliste" day={day} label="Abholliste" />
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};