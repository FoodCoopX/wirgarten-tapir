import React, { useState, useEffect } from 'react';
import { InfoCircle, ArrowRepeat } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadSpecificsPerDeliveryDay } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface DailySettingsModalProps {
  year: number;
  week: number;
  day: number;
  dayLabel: string;
  activeBreads: BreadList[];
  csrfToken: string;
}

interface SpecificsData {
  [breadId: string]: {
    minPieces: string;
    maxPieces: string;
    minRemainingPieces: string;
    fixedPieces: string;
  };
}

const FIELDS = [
  { key: 'minPieces' as const, label: 'Min. Stück', help: 'Mindestanzahl die gesamt gebacken werden soll' },
  { key: 'maxPieces' as const, label: 'Max. Stück', help: 'Maximale Anzahl die gesamt gebacken werden kann' },
  { key: 'minRemainingPieces' as const, label: 'Min. Rest', help: 'Direkte Bestellungen von Cafés etc.' },
  { key: 'fixedPieces' as const, label: 'Fixe Stück', help: 'exakte Anzahl für diesen Tag (wird im Backplan direkt so übernommen)' },
];

export const DailySettingsModal: React.FC<DailySettingsModalProps> = ({
  year,
  week,
  day,
  dayLabel,
  activeBreads,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [specifics, setSpecifics] = useState<SpecificsData>({});
  const [initialSpecifics, setInitialSpecifics] = useState<SpecificsData>({});

  useEffect(() => {
    if (show) {
      loadData();
    }
  }, [show, year, week, day]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !saving) {
        e.preventDefault();
        handleSaveAndClose();
      }
      if (e.key === 'Escape') {
        setShow(false);
      }
    };

    if (show) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [show, saving, specifics, initialSpecifics]);

  const loadData = async () => {
    setLoading(true);
    try {
      const existing = await bakeryApi.bakeryBreadSpecificsList({
        year,
        deliveryWeek: week,
        deliveryDay: day,
      });

      const initial: SpecificsData = {};
      activeBreads.forEach((bread) => {
        const entry = existing.find((e: BreadSpecificsPerDeliveryDay) => e.bread === bread.id);
        initial[bread.id!] = {
          minPieces: entry?.minPieces != null ? String(entry.minPieces) : '',
          maxPieces: entry?.maxPieces != null ? String(entry.maxPieces) : '',
          minRemainingPieces: entry?.minRemainingPieces != null ? String(entry.minRemainingPieces) : '',
          fixedPieces: entry?.fixedPieces != null ? String(entry.fixedPieces) : '',
        };
      });

      setSpecifics(initial);
      setInitialSpecifics(JSON.parse(JSON.stringify(initial)));
    } catch (error) {
      console.error('Failed to load bread specifics:', error);
      alert('Fehler beim Laden der Tageseinstellungen');
    } finally {
      setLoading(false);
    }
  };

   const getPlaceholder = (bread: BreadList, field: keyof SpecificsData[string]): string => {
    const fieldMap = {
      minPieces: bread.minPieces,
      maxPieces: bread.maxPieces,
      minRemainingPieces: bread.minRemainingPieces,
      fixedPieces: undefined, // fixed_pieces has no default in Bread model
    };
    
    const defaultValue = fieldMap[field];
    return defaultValue != null ? `${defaultValue}` : '-';
  };

  const handleCellChange = (breadId: string, field: keyof SpecificsData[string], value: string) => {
    const sanitized = value.trim();
    if (sanitized !== '' && isNaN(Number(sanitized))) return;

    setSpecifics((prev) => ({
      ...prev,
      [breadId]: {
        ...prev[breadId],
        [field]: sanitized,
      },
    }));
  };

  const handleSaveAndClose = async () => {
    setSaving(true);
    try {
      const updates: Array<{
        bread: string;
        minPieces: number | null;
        maxPieces: number | null;
        minRemainingPieces: number | null;
        fixedPieces: number | null;
      }> = [];

      Object.entries(specifics).forEach(([breadId, values]) => {
        const initial = initialSpecifics[breadId];
        const changed =
          values.minPieces !== initial?.minPieces ||
          values.maxPieces !== initial?.maxPieces ||
          values.minRemainingPieces !== initial?.minRemainingPieces ||
          values.fixedPieces !== initial?.fixedPieces;

        if (changed) {
          updates.push({
            bread: breadId,
            minPieces: values.minPieces === '' ? null : Number(values.minPieces),
            maxPieces: values.maxPieces === '' ? null : Number(values.maxPieces),
            minRemainingPieces: values.minRemainingPieces === '' ? null : Number(values.minRemainingPieces),
            fixedPieces: values.fixedPieces === '' ? null : Number(values.fixedPieces),
          });
        }
      });

      if (updates.length > 0) {
        await bakeryApi.bakeryBreadSpecificsBulkUpdateCreate({
          breadSpecificsPerDeliveryDayBulkUpdateRequest: {
            year,
            deliveryWeek: week,
            deliveryDay: day,
            updates,
          },
        });
      }

      setShow(false);
    } catch (error) {
      console.error('Failed to save bread specifics:', error);
      alert('Fehler beim Speichern der Tageseinstellungen');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button
        className="btn btn-sm w-100 mt-2"
        style={{
          backgroundColor: '#D4A574',
          color: 'white',
          border: '1px solid rgba(255,255,255,0.4)',
        }}
        onClick={() => setShow(true)}
      >
        <span
          className="material-icons me-2"
          style={{ fontSize: '16px', verticalAlign: 'middle' }}
        >
          settings
        </span>
        Tageseinstellungen
      </button>

      {show && (
        <>
          <div
            className="modal-backdrop fade show"
            onClick={() => setShow(false)}
            style={{ zIndex: 1040 }}
          />
          <div
            className="modal fade show d-block"
            tabIndex={-1}
            style={{ zIndex: 1050 }}
          >
            <div
              className={`modal-dialog ${activeBreads.length > 6 ? '' : 'modal-xl'} modal-dialog-centered modal-dialog-scrollable`}
              style={activeBreads.length > 6 ? { maxWidth: '95vw' } : {}}
            >
              <div className="modal-content">
                <div className="modal-header header-white-on-middle-brown">
                  <h5 className="modal-title">
                    <span
                      className="material-icons me-2"
                      style={{ fontSize: '20px', verticalAlign: 'middle' }}
                    >
                      settings
                    </span>
                    Tageseinstellungen — {dayLabel}, KW {week}/{year}
                  </h5>
                  {saving && (
                    <span className="badge bg-warning ms-2">
                      <ArrowRepeat size={14} className="me-1 spinner-grow-sm" />
                      Speichert...
                    </span>
                  )}
                  <button
                    type="button"
                    className="btn-close btn-close-white"
                    onClick={() => setShow(false)}
                  />
                </div>

                <div className="modal-body p-3">
                  {loading ? (
                    <div className="text-center py-5">
                      <div className="spinner-border" style={{ color: '#D4A574' }} />
                      <p className="mt-2 text-muted">Lade Daten...</p>
                    </div>
                  ) : activeBreads.length === 0 ? (
                    <div className="alert alert-info d-flex align-items-center" role="alert">
                      <InfoCircle size={20} className="me-2" />
                      Keine Brote für diesen Tag verfügbar. Aktiviere zuerst Brote im Wochenplan.
                    </div>
                  ) : (
                    <div className="card">
                      <div className="card-body p-0">
                        <div className="table-responsive">
                          <table className="table table-bordered table-hover mb-0">
                            <thead
                              style={{
                                backgroundColor: '#F5E6D3',
                                position: 'sticky',
                                top: 0,
                                zIndex: 10,
                              }}
                            >
                              <tr>
                                <th style={{ minWidth: '150px' }}>Brot</th>
                                {FIELDS.map((f) => (
                                  <th
                                    key={f.key}
                                    className="text-center"
                                    style={{ minWidth: '120px' }}
                                  >
                                    <div>{f.label}</div>
                                    <small className="text-muted d-block" style={{ fontWeight: 'normal', fontSize: '0.75rem' }}>
                                      {f.help}
                                    </small>
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {activeBreads.map((bread) => (
                                <tr key={bread.id}>
                                  <td className="fw-bold align-middle">
                                    <div className="d-flex align-items-center">
                                      {bread.picture && (
                                        <img
                                          src={bread.picture}
                                          alt={bread.name}
                                          className="me-2"
                                          style={{
                                            width: '32px',
                                            height: '32px',
                                            objectFit: 'cover',
                                            borderRadius: '6px',
                                          }}
                                        />
                                      )}
                                      {bread.name}
                                    </div>
                                  </td>
                                   {FIELDS.map((f) => (
                                    <td key={f.key} className="p-1">
                                      <input
                                        type="text"
                                        className="form-control form-control-sm text-center"
                                        value={specifics[bread.id!]?.[f.key] || ''}
                                        onChange={(e) =>
                                          handleCellChange(bread.id!, f.key, e.target.value)
                                        }
                                        placeholder={getPlaceholder(bread, f.key)}
                                        style={{
                                          minWidth: '60px',
                                          fontSize: '14px',
                                          fontWeight: specifics[bread.id!]?.[f.key] ? 'bold' : 'normal',
                                          color: specifics[bread.id!]?.[f.key] ? '#dd1755' : '#6c757d',
                                        }}
                                      />
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-secondary d-inline-flex align-items-center gap-1"
                    onClick={() => setShow(false)}
                    disabled={saving}
                  >
                    Abbrechen
                  </button>
                  <button
                    type="button"
                    className="btn d-inline-flex align-items-center gap-1 dark-brown-button"
                    onClick={handleSaveAndClose}
                    disabled={saving}
                  >
                    {saving ? (
                      <>
                        <span className="spinner-border spinner-border-sm" />
                        Speichert...
                      </>
                    ) : (
                      <>Speichern &amp; Schließen</>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};