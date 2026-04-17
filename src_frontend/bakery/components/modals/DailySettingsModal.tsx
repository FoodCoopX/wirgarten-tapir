import React, { useState, useEffect } from 'react';
import { InfoCircle, ArrowRepeat } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import TapirButton from '../../../components/TapirButton';
import { useApi } from '../../../hooks/useApi';
import { handleRequestError } from '../../../utils/handleRequestError';
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

  const loadData = () => {
    setLoading(true);
    bakeryApi.bakeryBreadSpecificsList({
      year,
      deliveryWeek: week,
      deliveryDay: day,
    })
      .then((existing) => {
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
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Laden der Tageseinstellungen');
      })
      .finally(() => {
        setLoading(false);
      });
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

  const handleSaveAndClose = () => {
    setSaving(true);

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

    if (updates.length === 0) {
      setShow(false);
      setSaving(false);
      return;
    }

    bakeryApi.bakeryBreadSpecificsBulkUpdateCreate({
      breadSpecificsPerDeliveryDayBulkUpdateRequest: {
        year,
        deliveryWeek: week,
        deliveryDay: day,
        updates,
      },
    })
      .then(() => {
        setShow(false);
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Speichern der Tageseinstellungen');
      })
      .finally(() => {
        setSaving(false);
      });
  };

  return (
    <>
      <TapirButton
        variant=""
        className="btn-bakery-primary w-100 mt-2"
        size="sm"
        icon="settings"
        text="Tageseinstellungen"
        onClick={() => setShow(true)}
        style={{ border: '1px solid rgba(255,255,255,0.4)' }}
      />

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
                      <div className="spinner-border spinner-bakery-primary" />
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
                              className="table-header-bakery"
                              style={{
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
                                        className={`form-control form-control-sm text-center ${specifics[bread.id!]?.[f.key] ? 'text-bakery-highlight fw-bold' : 'text-bakery-muted'}`}
                                        value={specifics[bread.id!]?.[f.key] || ''}
                                        onChange={(e) =>
                                          handleCellChange(bread.id!, f.key, e.target.value)
                                        }
                                        placeholder={getPlaceholder(bread, f.key)}
                                        style={{
                                          minWidth: '60px',
                                          fontSize: '14px',
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
                  <TapirButton
                    variant="secondary"
                    text="Abbrechen"
                    onClick={() => setShow(false)}
                    disabled={saving}
                  />
                  <TapirButton
                    variant=""
                    className="dark-brown-button"
                    text="Speichern & Schließen"
                    icon="save"
                    onClick={handleSaveAndClose}
                    loading={saving}
                  />
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};