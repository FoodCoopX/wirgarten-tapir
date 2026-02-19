import React, { useState, useEffect } from 'react';
import { YearWeekSelectorCard } from '../components/cards/YearWeekSelectorCard';
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

// Day labels mapping
const DAY_LABELS: Record<number, string> = {
  0: 'Montag',
  1: 'Dienstag',
  2: 'Mittwoch',
  3: 'Donnerstag',
  4: 'Freitag',
  5: 'Samstag',
  6: 'Sonntag',
};

export const Reports: React.FC = () => {
  const [year, setYear] = useState(currentYear);
  const [week, setWeek] = useState(currentWeek);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [days, setDays] = useState<DayConfig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDeliveryDays();
  }, []);

  const loadDeliveryDays = async () => {
    setLoading(true);
    try {
      const deliveryDaysData = await pickupLocationOpeningTimesApi.deliveryDays();
      
      const dayConfigs: DayConfig[] = deliveryDaysData.days.map((dayNumber) => ({
        day: dayNumber - 1, // Convert 1-7 to 0-6 for API
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

  const getDateForDay = (dayNumber: number): string => {
    const date = dayjs()
      .year(year)
      .isoWeek(week)
      .isoWeekday(dayNumber);
    return date.format('DD.MM.YYYY');
  };

  const handleDownload = async (reportType: 'backliste' | 'abholliste', day: number) => {
    const key = `${reportType}-${day}`;
    setDownloading(key);
    try {
      console.log('Download:', { reportType, year, week, day });
      
      // TODO: Download PDF from backend
      // const response = await fetch(`/bakery/reports/${reportType}/?year=${year}&week=${week}&day=${day}`);
      // const blob = await response.blob();
      // const url = window.URL.createObjectURL(blob);
      // const a = document.createElement('a');
      // a.href = url;
      // a.download = `${reportType}_${day}_KW${week}_${year}.pdf`;
      // a.click();
      
      alert(`${reportType} für Tag ${day}, KW ${week}/${year} wird heruntergeladen...`);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download fehlgeschlagen');
    } finally {
      setDownloading(null);
    }
  };

  const handleEmail = async (reportType: 'backliste' | 'abholliste', day: number) => {
    const key = `${reportType}-${day}`;
    setDownloading(key);
    try {
      console.log('Send email:', { reportType, year, week, day });
      
      // TODO: Send email via backend
      // await fetch(`/bakery/reports/${reportType}/email/`, {
      //   method: 'POST',
      //   body: JSON.stringify({ year, week, day }),
      // });
      
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
          days.map((dayConfig) => (
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
                            PDF herunterladen
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
                        Per E-Mail senden
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
                            PDF herunterladen
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
                        Per E-Mail senden
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};