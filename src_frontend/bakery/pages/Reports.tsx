import React, { useState, useEffect } from 'react';
import { BakeryApi, PickupLocationsApi } from '../../api-client';
import { useApi } from '../../hooks/useApi';
import type { AbhollisteResponse, PickupLocation, SolverPreviewDetailResponse } from '../../api-client/models';
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";
import { RunSolverCard, MetricsCard, YearWeekSelectorCard } from '../components/cards';
import {
  SectionToggle,
  BacklisteSection,
  OfenplanSection,
  VerteillisteSection,
  AbhollisteSection,
} from '../components/reports_components';
import '../styles/bakery_styles.css';

dayjs.extend(isoWeek);

const currentWeek = dayjs().isoWeek();
const currentYear = dayjs().year();

const DAY_LABELS: Record<number, string> = {
  0: 'Montag', 1: 'Dienstag', 2: 'Mittwoch', 3: 'Donnerstag',
  4: 'Freitag', 5: 'Samstag', 6: 'Sonntag',
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
  const [loading, setLoading] = useState(true);
  const [initialDataLoaded, setInitialDataLoaded] = useState(false);

  const [deliveryDays, setDeliveryDays] = useState<number[]>([]);
  const [allPickupLocations, setAllPickupLocations] = useState<PickupLocation[]>([]);
  const [breadCountsByDay, setBreadCountsByDay] = useState<Record<number, BreadCount[]>>({});
  const [stoveSessionsByDay, setStoveSessionsByDay] = useState<Record<number, StoveSessionGrouped[]>>({});
  const [previewByDay, setPreviewByDay] = useState<Record<number, SolverPreviewDetailResponse>>({});
  const [abhollisteByDayByLocation, setAbhollisteByDayByLocation] = useState<Record<number, Record<string, AbhollisteResponse>>>({});
  const [selectedPickupLocationByDay, setSelectedPickupLocationByDay] = useState<Record<number, string>>({});
  const [abhollisteLoadingByDay, setAbhollisteLoadingByDay] = useState<Record<number, boolean>>({});
  const [checkedByDay, setCheckedByDay] = useState<Record<number, Record<string, boolean>>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  const toggleSection = (key: string) => setOpenSections(prev => ({ ...prev, [key]: !prev[key] }));
  const isSectionOpen = (key: string) => openSections[key] ?? false;

  const getPickupLocationsForDay = (day: number) => allPickupLocations.filter(pl => pl.deliveryDay === day);
  const getDateForDay = (day: number) => dayjs().year(year).isoWeek(week).isoWeekday(day).format('DD.MM.YYYY');

  const handlePreviewDetail = (day: number, detail: SolverPreviewDetailResponse) => {
    setPreviewByDay(prev => ({ ...prev, [day]: detail }));
  };

  const handleApplied = () => {
    setPreviewByDay({});
    loadSolverResults();
    loadAllAbhollisten();
  };

  const handlePickupLocationChange = (day: number, id: string) => {
    setSelectedPickupLocationByDay(prev => ({ ...prev, [day]: id }));
    setCheckedByDay(prev => ({ ...prev, [day]: {} }));
  };

  const handleCheckToggle = (day: number, memberId: string) => {
    setCheckedByDay(prev => ({
      ...prev,
      [day]: { ...(prev[day] || {}), [memberId]: !prev[day]?.[memberId] },
    }));
  };

  // --- Data loading (unchanged logic) ---

  useEffect(() => { loadInitialData(); }, []);

  useEffect(() => {
    if (!initialDataLoaded) return;
    setPreviewByDay({});
    setBreadCountsByDay({});
    setStoveSessionsByDay({});
    setAbhollisteByDayByLocation({});
    setSelectedPickupLocationByDay({});
    setCheckedByDay({});
    loadSolverResults();
    loadAllAbhollisten();
  }, [year, week, initialDataLoaded]);

  useEffect(() => { loadSolverResults(); }, [year, week, deliveryDays, allPickupLocations]);

  useEffect(() => {
    if (deliveryDays.length > 0 && allPickupLocations.length > 0) loadAllAbhollisten();
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
      const allBreadCounts = await bakeryApi.bakeryBreadsPerPickupLocationPerWeekList({ year, deliveryWeek: week });
      const countsByDay: Record<number, BreadCount[]> = {};
      for (const entry of allBreadCounts) {
        const pl = allPickupLocations.find(p => p.id === String(entry.pickupLocation));
        if (!pl || pl.deliveryDay == null) continue;
        countsByDay[pl.deliveryDay] ??= [];
        countsByDay[pl.deliveryDay].push({
          breadId: String(entry.bread), breadName: entry.breadName || 'Unbekannt',
          pickupLocationId: String(entry.pickupLocation), pickupLocationName: pl.name, count: entry.count!,
        });
      }
      setBreadCountsByDay(countsByDay);

      const sessionsByDay: Record<number, StoveSessionGrouped[]> = {};
      for (const day of deliveryDays) {
        try {
          const sessions = await bakeryApi.bakeryStoveSessionsList({ year, deliveryWeek: week, deliveryDay: day });
          const grouped: Record<number, StoveSessionGrouped> = {};
          for (const s of sessions) {
            grouped[s.sessionNumber] ??= { session: s.sessionNumber, layers: [] };
            grouped[s.sessionNumber].layers.push({ layer: s.layerNumber, breadName: s.breadName || null, quantity: s.quantity! });
          }
          const sorted = Object.values(grouped).sort((a, b) => a.session - b.session);
          sorted.forEach(s => s.layers.sort((a, b) => a.layer - b.layer));
          if (sorted.length > 0) sessionsByDay[day] = sorted;
        } catch { /* no sessions */ }
      }
      setStoveSessionsByDay(sessionsByDay);
    } catch (error) {
      console.error('Failed to load solver results:', error);
    }
  };

  const loadAllAbhollisten = async () => {
    setAbhollisteLoadingByDay(deliveryDays.reduce((acc, day) => ({ ...acc, [day]: true }), {}));
    const data: Record<number, Record<string, AbhollisteResponse>> = {};
    for (const day of deliveryDays) {
      data[day] = {};
      await Promise.all(getPickupLocationsForDay(day).map(async (pl) => {
        try {
          data[day][pl.id!] = await bakeryApi.bakeryAbhollisteRetrieve({ year, deliveryWeek: week, pickupLocationId: pl.id! });
        } catch { data[day][pl.id!] = null as any; }
      }));
    }
    setAbhollisteByDayByLocation(data);
    setAbhollisteLoadingByDay(deliveryDays.reduce((acc, day) => ({ ...acc, [day]: false }), {}));
  };

  // --- Compute derived data per day ---

  const computeDayData = (day: number) => {
    const preview = previewByDay[day];
    const dayCounts = breadCountsByDay[day] || [];
    const daySessions = stoveSessionsByDay[day] || [];

    const breadDeliveries: Record<string, number> = {};
    const breadBaked: Record<string, number> = {};

    if (preview) {
      preview.quantities.forEach(q => {
        breadBaked[q.breadName] = (breadBaked[q.breadName] || 0) + q.total;
        breadDeliveries[q.breadName] = (breadDeliveries[q.breadName] || 0) + q.deliveries;
      });
    } else {
      dayCounts.forEach(c => { breadDeliveries[c.breadName] = (breadDeliveries[c.breadName] || 0) + c.count; });
      daySessions.forEach(s => s.layers.forEach(l => {
        if (l.breadName) breadBaked[l.breadName] = (breadBaked[l.breadName] || 0) + l.quantity;
      }));
    }

    const allBreadNames = [...new Set([...Object.keys(breadDeliveries), ...Object.keys(breadBaked)])].sort();
    const totalDeliveries = Object.values(breadDeliveries).reduce((s, c) => s + c, 0);
    const totalBaked = Object.values(breadBaked).reduce((s, c) => s + c, 0);

    const displaySessions: StoveSessionGrouped[] = preview
      ? preview.stoveSessions.map(s => ({ session: s.session, layers: s.layers.map(l => ({ layer: l.layer, breadName: l.breadName || null, quantity: l.quantity })) }))
      : daySessions;

    // Verteilliste data
    const locationBreads: Record<string, Record<string, { baked: number; ordered: number; extra: number }>> = {};
    const locationTotals: Record<string, { totalBaked: number; totalOrdered: number; totalExtra: number }> = {};
    const hasSolverResults = !!preview || dayCounts.length > 0;

    if (preview || dayCounts.length > 0) {
      const bakedByLoc: Record<string, Record<string, number>> = {};
      const orderedByLoc: Record<string, Record<string, number>> = {};

      if (preview) {
        preview.distribution.forEach(d => {
          bakedByLoc[d.pickupLocationName] ??= {};
          bakedByLoc[d.pickupLocationName][d.breadName] = (bakedByLoc[d.pickupLocationName][d.breadName] || 0) + d.count;
        });
      } else {
        dayCounts.forEach(c => {
          bakedByLoc[c.pickupLocationName] ??= {};
          bakedByLoc[c.pickupLocationName][c.breadName] = (bakedByLoc[c.pickupLocationName][c.breadName] || 0) + c.count;
        });
      }

      const dayAbhollisten = abhollisteByDayByLocation[day] || {};
      Object.entries(dayAbhollisten).forEach(([locationId, abhollisteData]) => {
        if (!abhollisteData) return;
        const location = allPickupLocations.find(pl => pl.id === locationId);
        if (!location) return;
        const bt = abhollisteData.breadTotals as unknown as Record<string, number>;
        if (bt) orderedByLoc[location.name] = { ...bt };
      });

      new Set([...Object.keys(bakedByLoc), ...Object.keys(orderedByLoc)]).forEach(locName => {
        const baked = bakedByLoc[locName] || {};
        const ordered = orderedByLoc[locName] || {};
        locationBreads[locName] = {};
        new Set([...Object.keys(baked), ...Object.keys(ordered)]).forEach(breadName => {
          const b = baked[breadName] || 0;
          const o = ordered[breadName] || 0;
          locationBreads[locName][breadName] = { baked: b, ordered: o, extra: b - o };
        });
      });
    } else {
      const dayAbhollisten = abhollisteByDayByLocation[day] || {};
      Object.entries(dayAbhollisten).forEach(([locationId, abhollisteData]) => {
        if (!abhollisteData) return;
        const location = allPickupLocations.find(pl => pl.id === locationId);
        if (!location) return;
        const bt = abhollisteData.breadTotals as unknown as Record<string, number>;
        const grandTotal = abhollisteData.grandTotal ?? 0;
        locationBreads[location.name] = {};
        let locTotalOrdered = 0;
        if (bt) {
          Object.entries(bt).forEach(([breadName, count]) => {
            locationBreads[location.name][breadName] = { baked: 0, ordered: count, extra: 0 };
            locTotalOrdered += count;
          });
        }
        locationTotals[location.name] = { totalBaked: grandTotal, totalOrdered: locTotalOrdered, totalExtra: grandTotal - locTotalOrdered };
      });
    }

    const distBreadNames = [...new Set(Object.values(locationBreads).flatMap(b => Object.keys(b)))].sort();

    return {
      preview, dayCounts, daySessions, breadDeliveries, breadBaked,
      allBreadNames, totalDeliveries, totalBaked, totalExtra: totalBaked - totalDeliveries,
      displaySessions, locationBreads, locationTotals, hasSolverResults, distBreadNames,
    };
  };

  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Berichte & Listen</h2>

      <div className="card mb-4">
        <div className="card-body">
          <YearWeekSelectorCard selectedYear={year} selectedWeek={week} onYearChange={setYear} onWeekChange={setWeek} />
        </div>
      </div>

      <div className="row">
        {loading ? (
          <div className="col-12 text-center py-5">
            <div className="spinner-border spinner-bakery-primary" />
            <p className="mt-2 text-muted">Lade Liefertage...</p>
          </div>
        ) : deliveryDays.length === 0 ? (
          <div className="col-12 text-center py-5">
            <p className="text-muted">Keine Liefertage konfiguriert</p>
          </div>
        ) : (
          deliveryDays.map((day) => {
            const d = computeDayData(day);
            const selectedLocation = selectedPickupLocationByDay[day] || '';
            const hasPreview = !!d.preview;

            return (
              <div key={day} className="col-lg-4 mb-4">
                <div className="card h-100">
                  <div className="card-header header-white-on-middle-brown">
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        <h5 className="mb-0">{DAY_LABELS[day] || `Tag ${day}`}</h5>
                        <small className="opacity-75">{getDateForDay(day)}</small>
                      </div>
                      <small>KW {week}</small>
                    </div>
                    <RunSolverCard
                    key={`solver-${year}-${week}-${day}`}
                      year={year} deliveryWeek={week} deliveryDay={day} csrfToken={csrfToken}
                      hasSavedPlan={d.daySessions.length > 0 || d.dayCounts.length > 0}
                      onPreviewDetail={(detail) => handlePreviewDetail(day, detail)}
                      onApplied={handleApplied}
                    />
                  </div>

                  <div className="card-body">
                    <BacklisteSection
                      isOpen={isSectionOpen(`backliste-${day}`)}
                      onToggle={() => toggleSection(`backliste-${day}`)}
                      allBreadNames={d.allBreadNames}
                      breadDeliveries={d.breadDeliveries}
                      breadBaked={d.breadBaked}
                      totalDeliveries={d.totalDeliveries}
                      totalBaked={d.totalBaked}
                      totalExtra={d.totalExtra}
                      pdfUrl={`/bakery/pdf/backliste/${year}/${week}/${day}/`}
                      hasPreview={hasPreview}
                      onEmail={() => {}}
                    />
                    <hr />

                    <div className="mb-3">
                      <SectionToggle
                        isOpen={isSectionOpen(`metrics-${day}`)}
                        onToggle={() => toggleSection(`metrics-${day}`)}
                        title="Präferenz-Zufriedenheit" icon="favorite"
                      />
                      <p className="text-muted small mb-2">Wie gut entspricht der Backplan den Mitgliederwünschen?</p>
                      {isSectionOpen(`metrics-${day}`) && (
                        d.displaySessions.length > 0
                          ? <MetricsCard year={year} week={week} deliveryDay={day} csrfToken={csrfToken} />
                          : <p className="text-muted small text-center py-2">Noch kein Backplan berechnet.</p>
                      )}
                    </div>
                    <hr />

                    <OfenplanSection
                      isOpen={isSectionOpen(`ofenplan-${day}`)}
                      onToggle={() => toggleSection(`ofenplan-${day}`)}
                      displaySessions={d.displaySessions}
                    />
                    <hr />

                    <VerteillisteSection
                      isOpen={isSectionOpen(`verteilliste-${day}`)}
                      onToggle={() => toggleSection(`verteilliste-${day}`)}
                      isLoading={abhollisteLoadingByDay[day] || false}
                      hasPreview={hasPreview}
                      hasSolverResults={d.hasSolverResults}
                      locationBreads={d.locationBreads}
                      locationTotals={d.locationTotals}
                      distBreadNames={d.distBreadNames}
                      pdfUrl={`/bakery/pdf/verteilliste/${year}/${week}/${day}/`}
                      onEmail={() => {}}
                    />
                    <hr />

                    <AbhollisteSection
                      isOpen={isSectionOpen(`abholliste-${day}`)}
                      onToggle={() => toggleSection(`abholliste-${day}`)}
                      isLoading={abhollisteLoadingByDay[day] || false}
                      hasPreview={hasPreview}
                      dayPickupLocations={getPickupLocationsForDay(day)}
                      selectedLocation={selectedLocation}
                      onPickupLocationChange={(id) => handlePickupLocationChange(day, id)}
                      abhollisteData={abhollisteByDayByLocation[day]?.[selectedLocation] || null}
                      checkedMembers={checkedByDay[day] || {}}
                      onCheckToggle={(memberId) => handleCheckToggle(day, memberId)}
                      pdfUrl={selectedLocation ? `/bakery/pdf/abholliste/${year}/${week}/${day}/${selectedLocation}/` : null}
                      allPdfUrl={`/bakery/pdf/abholliste-alle/${year}/${week}/${day}/`}
                      onEmail={() => {}}
                    />
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