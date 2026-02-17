import React, { useState, useEffect } from 'react';
import { configurationApi } from '../../types/client';
import type { BakeryConfiguration } from '../../types/api';

interface ConfigurationCardProps {
  onConfigChange?: (config: BakeryConfiguration) => void;
}

export const ConfigurationCard: React.FC<ConfigurationCardProps> = ({ onConfigChange }) => {
  const [config, setConfig] = useState<BakeryConfiguration>({
    pseudonyms_can_be_used: false,
    members_can_choose_breads: true,
    pickup_stations_can_be_chosen_per_share_not_just_per_member: false,
    days_backing_day_is_before_delivery_day: 1,
    days_choosing_day_is_before_backing_day: 1,
    days_pseudonym_can_be_changed_before_delivery: 1,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await configurationApi.get();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveField = async (updates: Partial<BakeryConfiguration>) => {
    setSaving(true);
    try {
      const updated = await configurationApi.update(updates);
      setConfig(updated);
      setLastSaved(new Date());
      if (onConfigChange) {
        onConfigChange(updated);
      }
    } catch (error) {
      console.error('Failed to save config:', error);
      await loadConfig();
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = (key: keyof BakeryConfiguration) => {
    const newValue = !config[key];
    setConfig({ ...config, [key]: newValue });
    saveField({ [key]: newValue });
  };

  const handleNumberChange = (key: keyof BakeryConfiguration, value: number) => {
    setConfig({ ...config, [key]: value });
    saveField({ [key]: value });
  };

  if (loading) {
    return (
      <div className="card">
        
        <div className="card-body text-center py-4">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Lädt...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <style>{`
        .bakery-switch .form-check-input:checked {
          background-color: #2E7D32 !important;
          border-color: #2E7D32 !important;
        }
      `}</style>
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">
          <span className="material-icons me-2" style={{ verticalAlign: 'middle' }}>settings</span>
          Bäckerei-Einstellungen
        </h5>
        {saving && (
          <span className="badge bg-warning">
            <span className="spinner-border spinner-border-sm me-1" />
            Speichert...
          </span>
        )}
       
      </div>
      
      <div className="card-body">
        {/* Pseudonyms Feature */}
        <div className="form-check form-switch bakery-switch mb-3">
          <input
            className="form-check-input"
            type="checkbox"
            id="pseudonyms_can_be_used"
            checked={config.pseudonyms_can_be_used}
            onChange={() => handleToggle('pseudonyms_can_be_used')}
          />
          <label className="form-check-label" htmlFor="pseudonyms_can_be_used">
            <strong>Pseudonyme aktivieren</strong>
            <br />
            <small className="text-muted">
              Mitglieder können Pseudonyme in Mitgliederlisten und Lieferungen verwenden
            </small>
          </label>
        </div>

        {/* Members Can Choose Breads */}
        <div className="form-check form-switch bakery-switch mb-3">
          <input
            className="form-check-input"
            type="checkbox"
            id="members_can_choose_breads"
            checked={config.members_can_choose_breads}
            onChange={() => handleToggle('members_can_choose_breads')}
          />
          <label className="form-check-label" htmlFor="members_can_choose_breads">
            <strong>Brotauswahl durch Mitglieder erlauben</strong>
            <br />
            <small className="text-muted">
              Mitglieder können ihre bevorzugten Brotsorten auswählen
            </small>
          </label>
        </div>

      

        {/* Pickup Stations Per Share */}
        <div className="form-check form-switch bakery-switch mb-3">
          <input
            className="form-check-input"
            type="checkbox"
            id="pickup_stations_per_share"
            checked={config.pickup_stations_can_be_chosen_per_share_not_just_per_member}
            onChange={() => handleToggle('pickup_stations_can_be_chosen_per_share_not_just_per_member')}
          />
          <label className="form-check-label" htmlFor="pickup_stations_per_share">
            <strong>Abholstationen pro Anteil wählen</strong>
            <br />
            <small className="text-muted">
              Mitglieder können ihre bevorzugten Abholstationen pro Anteil auswählen, nicht nur eine Abholstation pro Mitglied
            </small>
          </label>
        </div>

        <hr className="my-4" />
        <h6 className="text-muted mb-3">Zeitliche Abstände (in Tagen)</h6>

        {/* Days Backing Before Delivery */}
        <div className="mb-3">
          <label htmlFor="days_backing_day" className="form-label">
            <strong>Backtag vor Liefertag</strong>
          </label>
          <input
            type="number"
            className="form-control"
            id="days_backing_day"
            min="0"
            value={config.days_backing_day_is_before_delivery_day}
            onChange={(e) => handleNumberChange('days_backing_day_is_before_delivery_day', parseInt(e.target.value) || 0)}
          />
          <small className="text-muted">
            Anzahl Tage vor dem Liefertag, an dem gebacken wird
          </small>
        </div>

        {/* Days Choosing Before Backing */}
        <div className="mb-3">
          <label htmlFor="days_choosing_day" className="form-label">
            <strong>Wähltag vor Backtag</strong>
          </label>
          <input
            type="number"
            className="form-control"
            id="days_choosing_day"
            min="0"
            value={config.days_choosing_day_is_before_backing_day}
            onChange={(e) => handleNumberChange('days_choosing_day_is_before_backing_day', parseInt(e.target.value) || 0)}
          />
          <small className="text-muted">
            Anzahl Tage vor dem Backtag, an dem Mitglieder wählen können
          </small>
        </div>

        {/* Days Pseudonym Change Before Delivery */}
        <div className="mb-3">
          <label htmlFor="days_pseudonym_change" className="form-label">
            <strong>Pseudonym-Änderungsfrist vor Lieferung</strong>
          </label>
          <input
            type="number"
            className="form-control"
            id="days_pseudonym_change"
            min="0"
            value={config.days_pseudonym_can_be_changed_before_delivery}
            onChange={(e) => handleNumberChange('days_pseudonym_can_be_changed_before_delivery', parseInt(e.target.value) || 0)}
          />
          <small className="text-muted">
            Anzahl Tage vor dem Liefertag, bis wann Pseudonyme geändert werden können
          </small>
        </div>
      </div>
      
      <div className="card-footer text-muted">
        <small>
          <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>info</span>
          {' '}Änderungen werden automatisch gespeichert
        </small>
      </div>
    </div>
  );
};