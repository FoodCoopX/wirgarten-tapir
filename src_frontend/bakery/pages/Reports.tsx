import React, { useState, useEffect } from 'react';
import { YearWeekSelectorCard } from '../components/cards/YearWeekSelectorCard';
import { BakeryApi } from '../../api-client';
import { useApi } from '../../hooks/useApi';
import type { BreadDelivery } from '../../api-client/models';
import dayjs from "dayjs";
import isoWeek from "dayjs/plugin/isoWeek";

dayjs.extend(isoWeek);

interface DayConfig {
  day: number;
  label: string;
  dayNumber: number;
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
 
interface ReportsProps {
  csrfToken: string;
}

export const Reports: React.FC<ReportsProps> = ({ csrfToken }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [year, setYear] = useState(currentYear);
  const [week, setWeek] = useState(currentWeek);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [days, setDays] = useState<DayConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [deliveries, setDeliveries] = useState<BreadDelivery[]>([]);
  const [breadSummaryByDay, setBreadSummaryByDay] = useState<{
    [day: number]: { [breadName: string]: number };
  }>({});
  const [distributionByDay, setDistributionByDay] = useState<{
    [day: number]: { [pickupLocation: string]: { [breadName: string]: number } };
  }>({});

  useEffect(() => {
    loadDeliveryDays();
  }, []);

  useEffect(() => {
    loadBreadDeliveries();
  }, [year, week]);

  const loadDeliveryDays = async () => {
    setLoading(true);
    try {
      const deliveryDaysData = await bakeryApi.pickupLocationsApiDeliveryDaysRetrieve();
      
      const dayConfigs: DayConfig[] = deliveryDaysData.days.map((dayNumber: number) => ({
        day: dayNumber - 1,
        label: DAY_LABELS[dayNumber] || `Tag ${dayNumber}`,
        dayNumber: dayNumber,
      }));
      
      setDays(dayConfigs);
    } catch (error) {
      console.error('Failed to load delivery days:', error);
      alert('Fehler beim Laden der Liefertage');
    } finally {
      setLoading(false);
    }
  };

  const loadBreadDeliveries = async () => {
    try {
      const deliveriesData = await bakeryApi.bakeryBreadDeliveriesList({
        year,
        deliveryWeek: week,
      });
      setDeliveries(deliveriesData);

      // Calculate bread summary by day
      const summaryByDay: { [day: number]: { [breadName: string]: number } } = {};
      const distByDay: { [day: number]: { [pickupLocation: string]: { [breadName: string]: number } } } = {};
      
      deliveriesData.forEach(delivery => {
        const deliveryDay = delivery.deliveryDay;
        if (deliveryDay === undefined || deliveryDay === null) return;
        
        const breadName = delivery.breadName || 'Unbekannt';
        const pickupLocation = delivery.pickupLocationName || 'Unbekannt';
        
        // Summary by day
        if (!summaryByDay[deliveryDay]) {
          summaryByDay[deliveryDay] = {};
        }
        summaryByDay[deliveryDay][breadName] = (summaryByDay[deliveryDay][breadName] || 0) + 1;
        
        // Distribution by day and pickup location
        if (!distByDay[deliveryDay]) {
          distByDay[deliveryDay] = {};
        }
        if (!distByDay[deliveryDay][pickupLocation]) {
          distByDay[deliveryDay][pickupLocation] = {};
        }
        distByDay[deliveryDay][pickupLocation][breadName] = 
          (distByDay[deliveryDay][pickupLocation][breadName] || 0) + 1;
      });
      
      setBreadSummaryByDay(summaryByDay);
      setDistributionByDay(distByDay);
    } catch (error) {
      console.error('Failed to load bread deliveries:', error);
    }
  };

  const getDateForDay = (dayNumber: number): string => {
    const date = dayjs()
      .year(year)
      .isoWeek(week)
      .isoWeekday(dayNumber);
    return date.format('DD.MM.YYYY');
  };

  const handleDownload = async (reportType: 'backliste' | 'abholliste' | 'verteilungsliste', day: number) => {
    const key = `${reportType}-${day}`;
    setDownloading(key);
    try {
      console.log('Download:', { reportType, year, week, day });
      
      // TODO: Download PDF from backend
      
      alert(`${reportType} für Tag ${day}, KW ${week}/${year} wird heruntergeladen...`);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download fehlgeschlagen');
    } finally {
      setDownloading(null);
    }
  };

  const handleEmail = async (reportType: 'backliste' | 'abholliste' | 'verteilungsliste', day: number) => {
    const key = `${reportType}-${day}`;
    setDownloading(key);
    try {
      console.log('Send email:', { reportType, year, week, day });
      
      // TODO: Send email via backend
      
      alert(`${reportType} für Tag ${day}, KW ${week}/${year} wird per E-Mail versendet...`);
    } catch (error) {
      console.error('Email failed:', error);
      alert('E-Mail versenden fehlgeschlagen');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="container-fluid mt-4 px-5">
      <h2 className="mb-4">Berichte & Listen</h2>

      {/* Year/Week Selector */}
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

      {/* Day Columns */}
      <div className="row">
        {loading ? (
          <div className="col-12 text-center py-5">
            <div className="spinner-border" style={{ color: '#D4A574' }} />
            <p className="mt-2 text-muted">Lade Liefertage...</p>
          </div>
        ) : days.length === 0 ? (
          <div className="col-12 text-center py-5">
            <p className="text-muted">Keine Liefertage konfiguriert</p>
          </div>
        ) : (
          days.map((dayConfig) => {
            const daySummary = breadSummaryByDay[dayConfig.dayNumber] || {};
            const totalBreads = Object.values(daySummary).reduce((sum, count) => sum + count, 0);
            const dayDistribution = distributionByDay[dayConfig.dayNumber] || {};

            // Get all unique bread names for this day
            const allBreadNames = new Set<string>();
            Object.values(dayDistribution).forEach(location => {
              Object.keys(location).forEach(breadName => allBreadNames.add(breadName));
            });
            const sortedBreadNames = Array.from(allBreadNames).sort();

            return (
              <div key={dayConfig.day} className="col-lg-4 mb-4">
                <div className="card h-100">
                  <div 
                    className="card-header"
                    style={{ backgroundColor: '#D4A574', color: 'white' }}
                  >
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        <h5 className="mb-0">
                          {dayConfig.label}
                        </h5>
                        <small className="opacity-75">{getDateForDay(dayConfig.dayNumber)}</small>
                      </div>
                      <small>KW {week}</small>
                    </div>
                  </div>

                  <div className="card-body">
                    {/* Backliste Section */}
                    <div className="mb-4">
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>
                          bakery_dining
                        </span>
                        Backliste
                      </h6>
                      <p className="text-muted small mb-2">
                        Liste für die Bäckerei mit allen zu backenden Broten
                      </p>

                      {/* Bread Summary for this day */}
                      {Object.keys(daySummary).length > 0 && (
                        <div className="mb-3">
                          <div className="table-responsive">
                            <table className="table table-sm table-striped">
                              <thead style={{ backgroundColor: '#F5E6D3', fontSize: '0.85rem' }}>
                                <tr>
                                  <th>Brotsorte</th>
                                  <th className="text-end">Anzahl</th>
                                </tr>
                              </thead>
                              <tbody style={{ fontSize: '0.9rem' }}>
                                {Object.entries(daySummary)
                                  .sort(([nameA], [nameB]) => nameA.localeCompare(nameB))
                                  .map(([breadName, count]) => (
                                    <tr key={breadName}>
                                      <td>{breadName}</td>
                                      <td className="text-end">
                                        <strong style={{ color: '#8B4513' }}>{count}</strong>
                                      </td>
                                    </tr>
                                  ))}
                                <tr style={{ backgroundColor: '#F5E6D3', fontWeight: 'bold' }}>
                                  <td>Gesamt</td>
                                  <td className="text-end">{totalBreads}</td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      <div className="d-grid gap-2">
                        <button
                          className="btn btn-sm"
                          style={{ backgroundColor: '#8B6F47', color: 'white' }}
                          onClick={() => handleDownload('backliste', dayConfig.day)}
                          disabled={downloading === `backliste-${dayConfig.day}`}
                        >
                          {downloading === `backliste-${dayConfig.day}` ? (
                            <>
                              <span className="spinner-border spinner-border-sm me-2" />
                              Lädt...
                            </>
                          ) : (
                            <>
                              <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                                download
                              </span>
                              Backliste als PDF herunterladen
                            </>
                          )}
                        </button>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => handleEmail('backliste', dayConfig.day)}
                          disabled={downloading === `backliste-${dayConfig.day}`}
                        >
                          <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                            email
                          </span>
                          Backliste per E-Mail senden
                        </button>
                      </div>
                    </div>

                    <hr />

                    {/* Verteilungsliste Section */}
                    <div className="mb-4">
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>
                          warehouse
                        </span>
                        Verteilliste für Abholstationen
                      </h6>
                      <p className="text-muted small mb-2">
                        Übersicht wie viele Brote zu welcher Abholstation geliefert werden
                      </p>

                      {/* Distribution table */}
                      {Object.keys(dayDistribution).length > 0 && (
                        <div className="mb-3">
                          <div className="table-responsive">
                            <table className="table table-sm table-bordered" style={{ fontSize: '0.8rem' }}>
                              <thead style={{ backgroundColor: '#F5E6D3' }}>
                                <tr>
                                  <th style={{ writingMode: 'horizontal-tb' }}>Station</th>
                                  {sortedBreadNames.map(breadName => (
                                    <th key={breadName} className="text-center" style={{ 
                                      writingMode: 'vertical-rl',
                                      transform: 'rotate(180deg)',
                                      minWidth: '30px',
                                      maxWidth: '30px',
                                      padding: '8px 4px',
                                      fontSize: '0.75rem'
                                    }}>
                                      {breadName}
                                    </th>
                                  ))}
                                  <th className="text-center">Σ</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(dayDistribution)
                                  .sort(([nameA], [nameB]) => nameA.localeCompare(nameB))
                                  .map(([pickupLocation, breads]) => {
                                    const locationTotal = Object.values(breads).reduce((sum, count) => sum + count, 0);
                                    return (
                                      <tr key={pickupLocation}>
                                        <td style={{ fontSize: '0.75rem' }}>{pickupLocation}</td>
                                        {sortedBreadNames.map(breadName => (
                                          <td key={breadName} className="text-center">
                                            {breads[breadName] || '-'}
                                          </td>
                                        ))}
                                        <td className="text-center" style={{ fontWeight: 'bold', backgroundColor: '#F5E6D3' }}>
                                          {locationTotal}
                                        </td>
                                      </tr>
                                    );
                                  })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      <div className="d-grid gap-2">
                        <button
                          className="btn btn-sm"
                          style={{ backgroundColor: '#8B6F47', color: 'white' }}
                          onClick={() => handleDownload('verteilungsliste', dayConfig.day)}
                          disabled={downloading === `verteilungsliste-${dayConfig.day}`}
                        >
                          {downloading === `verteilungsliste-${dayConfig.day}` ? (
                            <>
                              <span className="spinner-border spinner-border-sm me-2" />
                              Lädt...
                            </>
                          ) : (
                            <>
                              <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                                download
                              </span>
                              Verteilliste als PDF herunterladen
                            </>
                          )}
                        </button>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => handleEmail('verteilungsliste', dayConfig.day)}
                          disabled={downloading === `verteilungsliste-${dayConfig.day}`}
                        >
                          <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                            email
                          </span>
                          Verteillisten per E-Mail senden
                        </button>
                      </div>
                    </div>

                    <hr />

                    {/* Abholliste Section */}
                    <div>
                      <h6 className="d-flex align-items-center mb-2">
                        <span className="material-icons me-2" style={{ fontSize: '18px' }}>
                          local_shipping
                        </span>
                        Abhollisten
                      </h6>
                      <p className="text-muted small mb-2">
                        Listen für die Abholorte mit Verteilung der Brote
                      </p>
                      <div className="d-grid gap-2">
                        <button
                          className="btn btn-sm"
                          style={{ backgroundColor: '#8B6F47', color: 'white' }}
                          onClick={() => handleDownload('abholliste', dayConfig.day)}
                          disabled={downloading === `abholliste-${dayConfig.day}`}
                        >
                          {downloading === `abholliste-${dayConfig.day}` ? (
                            <>
                              <span className="spinner-border spinner-border-sm me-2" />
                              Lädt...
                            </>
                          ) : (
                            <>
                              <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                                download
                              </span>
                              Abholliste als PDF herunterladen
                            </>
                          )}
                        </button>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => handleEmail('abholliste', dayConfig.day)}
                          disabled={downloading === `abholliste-${dayConfig.day}`}
                        >
                          <span className="material-icons me-2" style={{ fontSize: '16px', verticalAlign: 'middle' }}>
                            email
                          </span>
                          Abholliste per E-Mail senden
                        </button>
                      </div>
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