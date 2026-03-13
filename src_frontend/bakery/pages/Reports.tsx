import React, { useState, useEffect, useCallback } from 'react';
import { BakeryApi, PickupLocationsApi } from '../../api-client';
import { useApi } from '../../hooks/useApi';
import type { AbhollisteResponse, PickupLocation, SolverPreviewDetailResponse } from '../../api-client/models';
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";
import { RunSolverCard, MetricsCard, PreferredBreadStatisticsCard, YearWeekSelectorCard } from '../components/cards';
import { ChevronDown, ChevronRight } from 'react-bootstrap-icons';
import '../styles/bakery_styles.css';


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

interface BreadCount {
  breadId: string;
  breadName: string;
  pickupLocationId: string;
  pickupLocationName: string;
  count: number;
}

interface StoveSessionGrouped {
  session: number;
  layers: { layer: number; breadName: string | null; quantity: number }[];
}

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
  const [initialDataLoaded, setInitialDataLoaded] = useState(false);


  const [deliveryDays, setDeliveryDays] = useState<number[]>([]);
  const [allPickupLocations, setAllPickupLocations] = useState<PickupLocation[]>([]);

  // Data from BreadsPerPickupLocationPerWeek
  const [breadCountsByDay, setBreadCountsByDay] = useState<Record<number, BreadCount[]>>({});
  // Stove sessions
  const [stoveSessionsByDay, setStoveSessionsByDay] = useState<Record<number, StoveSessionGrouped[]>>({});
  const [previewByDay, setPreviewByDay] = useState<Record<number, SolverPreviewDetailResponse>>({});

  // Store Abholliste data for all locations by day
  const [abhollisteByDayByLocation, setAbhollisteByDayByLocation] = useState<
    Record<number, Record<string, AbhollisteResponse>>
  >({});

  const [selectedPickupLocationByDay, setSelectedPickupLocationByDay] = useState<Record<number, string>>({});
  const [abhollisteLoadingByDay, setAbhollisteLoadingByDay] = useState<Record<number, boolean>>({});
  const [checkedByDay, setCheckedByDay] = useState<Record<number, Record<string, boolean>>>({});

  // Toggle state per section per day
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  const toggleSection = (key: string) => {
    setOpenSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const isSectionOpen = (key: string) => openSections[key] ?? false;

    const handlePreviewDetail = (day: number, detail: SolverPreviewDetailResponse) => {
    setPreviewByDay(prev => ({ ...prev, [day]: detail }));
  };

  const handleApplied = () => {
    // Reload all data from DB after applying solver results
    setPreviewByDay({});
    loadSolverResults();
    loadAllAbhollisten();
  };


  useEffect(() => {
    loadInitialData();
  }, []);

  // When year/week changes, clear preview and reload week-specific data
  useEffect(() => {
    if (!initialDataLoaded) return;

    // Clear previous week's preview data
    setPreviewByDay({});
    setBreadCountsByDay({});
    setStoveSessionsByDay({});
    setAbhollisteByDayByLocation({});
    setSelectedPickupLocationByDay({});
    setCheckedByDay({});

    loadSolverResults();
    loadAllAbhollisten();
  }, [year, week, initialDataLoaded]);

  useEffect(() => {
    loadSolverResults();
  }, [year, week, deliveryDays, allPickupLocations]);

  // Load Abholliste for all pickup locations when year/week/deliveryDays change
  useEffect(() => {
    if (deliveryDays.length > 0 && allPickupLocations.length > 0) {
      loadAllAbhollisten();
    }
  }, [year, week, deliveryDays, allPickupLocations]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [deliveryDaysData, pickupLocations] = await Promise.all([
        bakeryApi.pickupLocationsApiDeliveryDaysRetrieve(),
        pickupLocationsApi.pickupLocationsPickupLocationsList(),
      ]);
      setDeliveryDays(deliveryDaysData.days);
      setAllPickupLocations(pickupLocations);
      setInitialDataLoaded(true);
    } catch (error) {
      console.error('Failed to load initial data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const loadSolverResults = async () => {
    if (deliveryDays.length === 0 || allPickupLocations.length === 0) return;

    try {
      // Load BreadsPerPickupLocationPerWeek for all days
      const allBreadCounts = await bakeryApi.bakeryBreadsPerPickupLocationPerWeekList({
        year,
        deliveryWeek: week,
      });

      // Group by delivery day (via pickup location)
      const countsByDay: Record<number, BreadCount[]> = {};
      for (const entry of allBreadCounts) {
        const pl = allPickupLocations.find(p => p.id === String(entry.pickupLocation));
        if (!pl) continue;
        const day = pl.deliveryDay;
        if (day == null) continue;
        countsByDay[day] ??= [];
        countsByDay[day].push({
          breadId: String(entry.bread),
          breadName: entry.breadName || 'Unbekannt',
          pickupLocationId: String(entry.pickupLocation),
          pickupLocationName: pl.name,
          count: entry.count!,
        });
      }
      setBreadCountsByDay(countsByDay);

      // Load stove sessions per day
      const sessionsByDay: Record<number, StoveSessionGrouped[]> = {};
      for (const day of deliveryDays) {
        try {
          const sessions = await bakeryApi.bakeryStoveSessionsList({
            year,
            deliveryWeek: week,
            deliveryDay: day,
          });

          // Group by session number
          const grouped: Record<number, StoveSessionGrouped> = {};
          for (const s of sessions) {
            grouped[s.sessionNumber] ??= { session: s.sessionNumber, layers: [] };
            grouped[s.sessionNumber].layers.push({
              layer: s.layerNumber,
              breadName: s.breadName || null,
              quantity: s.quantity!,
            });
          }
          const sorted = Object.values(grouped).sort((a, b) => a.session - b.session);
          sorted.forEach(s => s.layers.sort((a, b) => a.layer - b.layer));
          if (sorted.length > 0) {
            sessionsByDay[day] = sorted;
          }
        } catch {
          // No sessions for this day
        }
      }
      setStoveSessionsByDay(sessionsByDay);
    } catch (error) {
      console.error('Failed to load solver results:', error);
    }
  };

  // Load Abholliste for all pickup locations (for Verteilliste aggregation)
  const loadAllAbhollisten = async () => {
    setAbhollisteLoadingByDay(
      deliveryDays.reduce((acc, day) => ({ ...acc, [day]: true }), {})
    );

    const dataByDayByLocation: Record<number, Record<string, AbhollisteResponse>> = {};

    for (const day of deliveryDays) {
      dataByDayByLocation[day] = {};
      const dayLocations = getPickupLocationsForDay(day);

      await Promise.all(
        dayLocations.map(async (pl) => {
          try {
            const data = await bakeryApi.bakeryAbhollisteRetrieve({
              year,
              deliveryWeek: week,
              pickupLocationId: pl.id!,
            });
            dataByDayByLocation[day][pl.id!] = data;
          } catch (error) {
            console.error(`Failed to load Abholliste for ${pl.name}:`, error);
            dataByDayByLocation[day][pl.id!] = null as any;
          }
        })
      );
    }

    setAbhollisteByDayByLocation(dataByDayByLocation);
    setAbhollisteLoadingByDay(
      deliveryDays.reduce((acc, day) => ({ ...acc, [day]: false }), {})
    );
  };
  const getPickupLocationsForDay = (day: number): PickupLocation[] =>
    allPickupLocations.filter(pl => pl.deliveryDay === day);

  const getDateForDay = (day: number): string =>
    dayjs().year(year).isoWeek(week).isoWeekday(day).format('DD.MM.YYYY');

  const handlePickupLocationChange = (day: number, pickupLocationId: string) => {
    setSelectedPickupLocationByDay(prev => ({ ...prev, [day]: pickupLocationId }));
    setCheckedByDay(prev => ({ ...prev, [day]: {} }));
  };

  const handleCheckToggle = (day: number, memberId: string) => {
    setCheckedByDay(prev => ({
      ...prev,
      [day]: { ...(prev[day] || {}), [memberId]: !prev[day]?.[memberId] },
    }));
  };

  const handleEmail = async (reportType: string, day: number) => {
    setDownloading(`${reportType}-${day}`);
    try {
      alert(`${reportType} für KW ${week}/${year} wird per E-Mail versendet...`);
    } finally {
      setDownloading(null);
    }
  };


  const SectionToggle = ({ sectionKey, title, icon }: { sectionKey: string; title: string; icon: string }) => (
    <h6
      className="d-flex align-items-center mb-2"
      style={{ cursor: 'pointer', userSelect: 'none' }}
      onClick={() => toggleSection(sectionKey)}
    >
      {isSectionOpen(sectionKey) ? <ChevronDown size={16} className="me-1" /> : <ChevronRight size={16} className="me-1" />}
      <span className="material-icons me-2" style={{ fontSize: '18px' }}>{icon}</span>
      {title}
    </h6>
  );

  const ActionButtons = ({ reportType, day, label }: { reportType: string; day: number; label: string }) => {
    const key = `${reportType}-${day}`;

    let pdfUrl: string | null = null;
    if (reportType === 'backliste') {
      pdfUrl = `/bakery/pdf/backliste/${year}/${week}/${day}/`;
    } else if (reportType === 'verteilungsliste') {
      pdfUrl = `/bakery/pdf/verteilliste/${year}/${week}/${day}/`;
    } else if (reportType === 'abholliste') {
      const selectedLoc = selectedPickupLocationByDay[day];
      if (selectedLoc) {
        pdfUrl = `/bakery/pdf/abholliste/${year}/${week}/${day}/${selectedLoc}/`;
      }
    }

    const hasPreview = !!previewByDay[day];

    return (
      <div className="d-grid gap-2">
        {hasPreview && (
          <div className="alert alert-warning py-1 px-2 mb-1" style={{ fontSize: '0.75rem' }}>
            <span className="material-icons me-1" style={{ fontSize: '12px', verticalAlign: 'middle' }}>warning</span>
            Vorschau aktiv — PDF wird aus gespeicherten Daten erstellt.
            Erst „Anwenden", dann PDF herunterladen.
          </div>
        )}
        {pdfUrl ? (
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-sm dark-brown-button text-decoration-none"
          >
            <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>download</span>
            {label} als PDF herunterladen
          </a>
        ) : (
          <button className="btn btn-sm dark-brown-button" disabled>
            <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>download</span>
            {label} als PDF herunterladen
          </button>
        )}
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
            const preview = previewByDay[day];

            const dayCounts = breadCountsByDay[day] || [];
            const daySessions = stoveSessionsByDay[day] || [];

            // Use preview data if available, otherwise fall back to saved DB data
            const breadDeliveries: Record<string, number> = {};
            const breadBaked: Record<string, number> = {};

            if (preview) {
              // From preview detail: quantities
              preview.quantities.forEach(q => {
                breadBaked[q.breadName] = (breadBaked[q.breadName] || 0) + q.total;
                breadDeliveries[q.breadName] = (breadDeliveries[q.breadName] || 0) + q.deliveries;
              });
            } else {
              // From saved DB data
              dayCounts.forEach(c => {
                breadDeliveries[c.breadName] = (breadDeliveries[c.breadName] || 0) + c.count;
              });
              daySessions.forEach(session => {
                session.layers.forEach(layer => {
                  if (layer.breadName) {
                    breadBaked[layer.breadName] = (breadBaked[layer.breadName] || 0) + layer.quantity;
                  }
                });
              });
            }

            // Combine all bread names
            const allBreadNames = [...new Set([...Object.keys(breadDeliveries), ...Object.keys(breadBaked)])].sort();

            // Calculate totals
            const totalDeliveries = Object.values(breadDeliveries).reduce((s, c) => s + c, 0);
            const totalBaked = Object.values(breadBaked).reduce((s, c) => s + c, 0);
            const totalExtra = totalBaked - totalDeliveries;

            // Build stove sessions display from preview or saved data
            const displaySessions: StoveSessionGrouped[] = preview
              ? preview.stoveSessions.map(s => ({
                  session: s.session,
                  layers: s.layers.map(l => ({
                    layer: l.layer,
                    breadName: l.breadName || null,
                    quantity: l.quantity,
                  })),
                }))
              : daySessions;

            // Verteilliste: Use preview, solver results, or aggregate from Abholliste
            const locationBreads: Record<string, Record<string, number>> = {};
            const hasSolverResults = !!preview || dayCounts.length > 0;

            if (preview) {
              // From preview distribution
              preview.distribution.forEach(d => {
                locationBreads[d.pickupLocationName] ??= {};
                locationBreads[d.pickupLocationName][d.breadName] =
                  (locationBreads[d.pickupLocationName][d.breadName] || 0) + d.count;
              });
            } else if (dayCounts.length > 0) {
              // From saved DB data
              dayCounts.forEach(c => {
                locationBreads[c.pickupLocationName] ??= {};
                locationBreads[c.pickupLocationName][c.breadName] =
                  (locationBreads[c.pickupLocationName][c.breadName] || 0) + c.count;
              });
              } else {
              // Aggregate from Abholliste data — no solver results yet
              const dayAbhollistenByLocation = abhollisteByDayByLocation[day] || {};
              Object.entries(dayAbhollistenByLocation).forEach(([locationId, abhollisteData]) => {
                if (!abhollisteData) return;
                const location = allPickupLocations.find(pl => pl.id === locationId);
                if (!location) return;

                // Use grandTotal from the API response directly
                const locationTotal = abhollisteData.grandTotal ?? 0;
                console.log(`Verteilliste fallback: ${location.name} = ${locationTotal}`, abhollisteData);
                if (locationTotal > 0) {
                  locationBreads[location.name] = { __total: locationTotal };
                }
              });
            }

            const distBreadNames = [...new Set(
              Object.values(locationBreads).flatMap(breads => Object.keys(breads))
            )].sort();

            const dayPickupLocations = getPickupLocationsForDay(day);
            const selectedLocation = selectedPickupLocationByDay[day] || '';
         
            const abhollisteLoading = abhollisteLoadingByDay[day] || false;
            const dayChecked = checkedByDay[day] || {};

  
            const backlisteKey = `backliste-${day}`;
            const ofenplanKey = `ofenplan-${day}`;
            const verteillisteKey = `verteilliste-${day}`;
            const abhollisteKey = `abholliste-${day}`;
            const metricsKey = `metrics-${day}`;
            const statisticKey = `statistic-${day}`;

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
                   
                   
                   <RunSolverCard
                      year={year}
                      deliveryWeek={week}
                      deliveryDay={day}
                      csrfToken={csrfToken}
                      hasSavedPlan={daySessions.length > 0 || dayCounts.length > 0}
                      onPreviewDetail={(detail) => handlePreviewDetail(day, detail)}
                      onApplied={handleApplied}
                    />
                    
                  </div>

                  <div className="card-body">

                    {/* Backliste */}
                    <div className="mb-3">
                      <SectionToggle sectionKey={backlisteKey} title="Backliste" icon="bakery_dining" />

                      {isSectionOpen(backlisteKey) && (
                        <>
                          {allBreadNames.length > 0 ? (<>
                            <div className="table-responsive mb-3">
                             <table className="table table-sm" style={{ fontSize: '0.8rem' }}>
                                <thead style={{ backgroundColor: '#F5E6D3', fontSize: '0.8rem' }}>
                                  <tr className="total-row-brown">
                                    <th>Brotsorte</th>
                                    <th className="text-end" title="Zuweisung zu Verteilstationen">
                                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>local_shipping</span>
                                    </th>
                                    <th className="text-end" title="Extra (Reserve/Verkauf)">
                                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>add_circle</span>
                                    </th>
                                    <th className="text-end" title="Gesamt im Ofen gebacken">
                                      <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>local_fire_department</span>
                                    </th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {allBreadNames.map((name) => {
                                    const deliveries = breadDeliveries[name] || 0;
                                    const baked = breadBaked[name] || 0;
                                    const extra = baked - deliveries;
                                    return (
                                      <tr key={name}>
                                        <td>{name}</td>
                                        <td className="text-end">{deliveries}</td>
                                        <td className="text-end" style={{ color: extra > 0 ? '#28a745' : '#6c757d' }}>
                                          {extra > 0 ? `+${extra}` : extra}
                                        </td>
                                        <td className="text-end">
                                          <strong style={{ color: '#8B4513' }}>{baked}</strong>
                                        </td>
                                      </tr>
                                    );
                                  })}
                                  <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                    <td>Gesamt</td>
                                    <td className="text-end">{totalDeliveries}</td>
                                    <td className="text-end" style={{ color: totalExtra > 0 ? '#28a745' : '#6c757d' }}>
                                      {totalExtra > 0 ? `+${totalExtra}` : totalExtra}
                                    </td>
                                    <td className="text-end">{totalBaked}</td>
                                  </tr>
                                </tbody>
                              </table>
                              <div className="text-muted small">
                                <p className="mb-1">
                                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>local_shipping</span> = Zuweisung zu Verteilstationen
                                </p>
                                <p className="mb-1">
                                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>add_circle</span> = Extra (Reserve/Verkauf)
                                </p>
                                <p className="mb-0">
                                  <span className="material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>local_fire_department</span> = Gesamt im Ofen gebacken
                                </p>
                              </div>
                            </div>
                            <ActionButtons reportType="backliste" day={day} label="Backliste" />
                          </>) : (
                            <p className="text-muted small text-center py-2">
                              Noch kein Backplan berechnet.
                            </p>
                          )}
                        </>
                      )}
                    </div>

                    <hr />

                    {/* Metrics Section */}
                    <div className="mb-3">
                      <SectionToggle
                        sectionKey={metricsKey}
                        title="Präferenz-Zufriedenheit"
                        icon="favorite"
                      />
                      <p className="text-muted small mb-2">
                        Wie gut entspricht der Backplan den Mitgliederwünschen?
                      </p>

                      {isSectionOpen(metricsKey) && (
                        <>
                          {displaySessions.length > 0 ? (
                            <MetricsCard year={year} week={week} deliveryDay={day} csrfToken={csrfToken} />
                          ) : (
                            <p className="text-muted small text-center py-2">
                              Noch kein Backplan berechnet.
                            </p>
                          )}
                        </>
                      )}
                    </div>

                    <hr />

                    {/* Ofenplan */}
                    <div className="mb-3">
                      <SectionToggle sectionKey={ofenplanKey} title="Ofenplan" icon="local_fire_department" />
                      <p className="text-muted small mb-2">Belegung der Ofengänge</p>

                      {isSectionOpen(ofenplanKey) && (
                        <>
                          {displaySessions.length > 0 ? (
                            <div className="d-flex flex-column gap-2 mb-3">
                              {displaySessions.map((session) => (
                                <div key={session.session} className="card">
                                  <div
                                    className="card-header py-1"
                                    style={{ backgroundColor: '#D4A574', color: 'white' }}
                                  >
                                    <small className="fw-bold">Ofengang {session.session}</small>
                                  </div>
                                  <ul className="list-group list-group-flush">
                                    {session.layers.map((layer) => (
                                      <li key={layer.layer} className="list-group-item py-1 small">
                                        <span className="text-muted">Etage {layer.layer}:</span>{' '}
                                        {layer.breadName ? (
                                          <span>
                                            {layer.breadName}{' '}
                                            <span className="badge bg-secondary">×{layer.quantity}</span>
                                          </span>
                                        ) : (
                                          <span className="text-muted fst-italic">leer</span>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-muted small text-center py-2">
                              Noch kein Ofenplan berechnet.
                            </p>
                          )}
                        </>
                      )}
                    </div>

                    <hr />

                    {/* Verteilliste */}
                    <div className="mb-3">
                      <SectionToggle sectionKey={verteillisteKey} title="Verteilliste" icon="warehouse" />
                      <p className="text-muted small mb-2">
                        {preview
                          ? 'Brote pro Abholstation (Vorschau)'
                          : hasSolverResults
                            ? 'Brote pro Abholstation (lt. Backplan)'
                            : 'Brote pro Abholstation (lt. Mitgliederbestellungen)'}
                      </p>

                        {isSectionOpen(verteillisteKey) && (
                        <>
                          {abhollisteLoading ? (
                            <div className="text-center py-3">
                              <div className="spinner-border spinner-border-sm" style={{ color: '#D4A574' }} />
                              <p className="mt-1 text-muted small">Lade Daten...</p>
                            </div>
                          ) : Object.keys(locationBreads).length > 0 ? (
                            <>
                              {!hasSolverResults && (
                                <div className="alert alert-info alert-sm mb-2" style={{ fontSize: '0.75rem', padding: '0.5rem' }}>
                                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>info</span>
                                  {' '}Basierend auf Mitgliederbestellungen (noch kein Backplan)
                                </div>
                              )}
                              {preview && (
                                <div className="alert alert-warning alert-sm mb-2" style={{ fontSize: '0.75rem', padding: '0.5rem' }}>
                                  <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>preview</span>
                                  {' '}Vorschau – noch nicht gespeichert
                                </div>
                              )}
                              <div className="table-responsive mb-3">
                                {hasSolverResults ? (
                                  <table className="table table-sm" style={{ fontSize: '0.8rem' }}>
                                <thead>
                                  <tr className="total-row-brown">
                                        <th>Station</th>
                                        {distBreadNames.map(name => (
                                          <th key={name} className="text-center" style={{
                                            minWidth: '30px', maxWidth: '60px', padding: '8px 4px', fontSize: '0.6rem',
                                          }}>{name}</th>
                                        ))}
                                        <th className="text-center">Σ</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {Object.entries(locationBreads).sort(([a], [b]) => a.localeCompare(b)).map(([loc, breads]) => {
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
                                ) : (
                                  <table className="table table-sm table-bordered" style={{ fontSize: '0.8rem' }}>
                                    <thead style={{ backgroundColor: '#F5E6D3' }}>
                                      <tr>
                                        <th>Station</th>
                                        <th className="text-center">Brote</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {Object.entries(locationBreads).sort(([a], [b]) => a.localeCompare(b)).map(([loc, breads]) => (
                                        <tr key={loc}>
                                          <td style={{ fontSize: '0.75rem' }}>{loc}</td>
                                          <td className="text-center" style={{ fontWeight: 'bold', color: '#8B4513' }}>
                                            {breads.__total || 0}
                                          </td>
                                        </tr>
                                      ))}
                                      <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                        <td>Gesamt</td>
                                        <td className="text-center">
                                          {Object.values(locationBreads).reduce((s, b) => s + (b.__total || 0), 0)}
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                )}
                              </div>
                            </>
                          ) : (
                            <p className="text-muted small text-center py-2">
                              Keine Daten verfügbar.
                            </p>
                          )}
                          <ActionButtons reportType="verteilungsliste" day={day} label="Verteilliste" />
                        </>
                      )}
                    </div>

                    <hr />

                    {/* Abholliste */}
                    <div>
                      <SectionToggle sectionKey={abhollisteKey} title="Abholliste" icon="local_shipping" />
                      <p className="text-muted small mb-2">Brote pro Mitglied am Abholort</p>

                      {isSectionOpen(abhollisteKey) && (
                        <>
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
                           <ActionButtons reportType="abholliste" day={day} label="Abholliste" />
                            <div className="mt-2">
                            <a
                              href={`/bakery/pdf/abholliste-alle/${year}/${week}/${day}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-sm dark-brown-button w-100 text-decoration-none"
                            >
                              <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>picture_as_pdf</span>
                              Alle Abhollisten als ein PDF
                            </a>
                          </div>

                          {abhollisteLoading ? (
                            <div className="text-center py-3">
                              <div className="spinner-border spinner-border-sm" style={{ color: '#D4A574' }} />
                              <p className="mt-1 text-muted small">Lade Abholliste...</p>
                            </div>
                          ) : selectedLocation && (() => {
                            const abhollisteData = abhollisteByDayByLocation[day]?.[selectedLocation];
                            if (!abhollisteData || !abhollisteData.entries || abhollisteData.entries.length === 0) {
                              return (
                                <p className="text-muted small text-center py-2">
                                  Keine Brotbestellungen für diesen Abholort.
                                </p>
                              );
                            }

                            const entries = abhollisteData.entries;
                            const breadNames: string[] = abhollisteData.breadNames;
                            const breadTotals: Record<string, number> = abhollisteData.breadTotals as unknown as Record<string, number>;
                            const grandTotal: number = abhollisteData.grandTotal;
                            return (
                              <>
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
                                        {breadNames.map(name => (
                                          <th key={name} className="text-center" style={{
                                            writingMode: 'vertical-rl', transform: 'rotate(180deg)',
                                            minWidth: '28px', maxWidth: '28px', padding: '8px 2px', fontSize: '0.7rem',
                                          }}>{name}</th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {entries.map((entry: any, index: number) => {
                                        const memberId = entry.memberId || entry.member_id;
                                        const displayName = entry.displayName || entry.display_name;
                                        const totalBreads = entry.totalBreads || entry.total_breads || 0;
                                        const breadCounts: Record<string, number> = entry.breadCounts || entry.bread_counts || {};
                                        const breadPreferred: Record<string, boolean> = entry.breadPreferred || entry.bread_preferred || {};
                                        const isChecked = dayChecked[memberId] || false;

                                        return (
                                          <tr key={memberId} style={{
                                            backgroundColor: isChecked ? '#d4edda' : undefined,
                                            textDecoration: isChecked ? 'line-through' : undefined,
                                            opacity: isChecked ? 0.7 : 1,
                                          }}>
                                            <td className="text-center text-muted">{index + 1}</td>
                                            <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{displayName}</td>
                                            <td className="text-center">
                                              <strong style={{ color: '#8B4513' }}>{totalBreads}</strong>
                                            </td>
                                            <td className="text-center">
                                              <input
                                                type="checkbox" className="form-check-input"
                                                checked={isChecked}
                                                onChange={() => handleCheckToggle(day, memberId)}
                                                style={{ cursor: 'pointer' }}
                                              />
                                            </td>
                                            {breadNames.map(name => {
                                              const count = breadCounts[name] || 0;
                                              const preferred = breadPreferred[name] || false;
                                              return (
                                                <td
                                                  key={name}
                                                  className="text-center"
                                                  style={{
                                                    backgroundColor: preferred ? '#d4edda' : undefined,
                                                    color: count > 0 ? '#212529' : '#ccc',
                                                  }}
                                                >
                                                  {count > 0 ? count : preferred ? '' : '—'}
                                                </td>
                                              );
                                            })}
                                          </tr>
                                        );
                                      })}
                                      <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                        <td />
                                        <td>Gesamt</td>
                                        <td className="text-center">{grandTotal}</td>
                                        <td className="text-center">
                                        </td>
                                        {breadNames.map(name => (
                                          <td key={name} className="text-center">{breadTotals[name] || 0}</td>
                                        ))}
                                      </tr>
                                    </tbody>
                                  </table>
                                </div>
                                <div className="d-flex align-items-center gap-2 mb-2" style={{ fontSize: '0.75rem' }}>
                                  <span style={{
                                    display: 'inline-block', width: '14px', height: '14px',
                                    backgroundColor: '#d4edda', border: '1px solid #c3e6cb',
                                  }} />
                                  <span className="text-muted">= als Lieblingsbrot angegeben</span>
                                </div>
                              </>
                            );
                          })()}

                         
                        </>
                      )}
                    </div>
                    
                    <hr />

                    {/* Statistik Lieblingsbrote */}
                    <div className="mb-3">
                      <SectionToggle
                        sectionKey={statisticKey}
                        title="Statistik Lieblingsbrote"
                        icon="favorite"
                      />

                      {isSectionOpen(statisticKey) && (
                        <div className="mt-3">
                          <h6 className="d-flex align-items-center mb-2" style={{ fontSize: '0.85rem' }}>
                            <span className="material-icons me-2" style={{ fontSize: '16px', color: '#D4A574' }}>bar_chart</span>
                            Lieblingsbrote
                          </h6>
                          <PreferredBreadStatisticsCard
                            year={year}
                            week={week}
                            deliveryDay={day}
                            csrfToken={csrfToken}
                          />
                        </div>
                      )}
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