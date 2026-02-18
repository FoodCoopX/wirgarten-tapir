import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { PlusLg, XLg, Trash } from 'react-bootstrap-icons';
import type { BreadLabel, BreadList, BreadListRequest } from '../../../api-client/models';

interface BreadModalProps {
  bread: BreadList | null;
  csrfToken: string;
  onSave: (bread: BreadListRequest) => void;
  onClose: () => void;
}

export const BreadModal: React.FC<BreadModalProps> = ({ bread, csrfToken, onSave, onClose }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [formData, setFormData] = useState<BreadListRequest>({
    name: '',
    description: '',
    weight: '500',
    isActive: true,
    labels: [] as string[],
    
  });
  const [availableLabels, setAvailableLabels] = useState<BreadLabel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLabels();
    if (bread) {
      const labelIds = Array.isArray(bread.labels)
        ? bread.labels.map(label => typeof label === 'object' ? label.id : String(label))
        : [];

      setFormData({
        name: bread.name,
        description: bread.description || '',
        weight: String(bread.weight),
        isActive: bread.isActive,
        labels: labelIds,
      });
    }
  }, [bread]);

  const loadLabels = async () => {
    setLoading(true);
    try {
      const data = await bakeryApi.bakeryLabelsList();
      setAvailableLabels(data);
    } catch (error) {
      console.error('Failed to load labels:', error);
      alert('Fehler beim Laden der Labels');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const toggleLabel = (labelId: string) => {
    setFormData(prev => ({
      ...prev,
      labels: prev.labels.includes(labelId)
        ? prev.labels.filter(id => id !== labelId)
        : [...prev.labels, labelId]
    }));
  };

  const assignedLabels = availableLabels.filter(label => formData.labels.includes(label.id));
  const unassignedLabels = availableLabels.filter(label => !formData.labels.includes(label.id));

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header" style={{ backgroundColor: '#F5E6D3', color: '#8B4513' }}>
            <h5 className="modal-title">
              {bread ? 'Brot bearbeiten' : 'Neues Brot'}
            </h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-md-8">
                  <div className="mb-3">
                    <label htmlFor="name" className="form-label fw-bold">
                      Name <span className="text-danger">*</span>
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                      placeholder="z.B. Vollkornbrot"
                    />
                  </div>
                </div>

                <div className="col-md-4">
                  <div className="mb-3">
                    <label htmlFor="weight" className="form-label fw-bold">
                      Gewicht (g) <span className="text-danger">*</span>
                    </label>
                    <input
                      type="number"
                      className="form-control"
                      id="weight"
                      value={formData.weight}
                      onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                      required
                      min="0"
                      step="10"
                    />
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label htmlFor="description" className="form-label fw-bold">
                  Beschreibung
                </label>
                <textarea
                  className="form-control"
                  id="description"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Beschreibung des Brots..."
                />
              </div>

              <div className="mb-3">
                <label className="form-label fw-bold">
                  Labels
                  {formData.labels.length > 0 && (
                    <span className="badge bg-success ms-2">{formData.labels.length}</span>
                  )}
                </label>
                
                {loading ? (
                  <div className="text-center py-3">
                    <div className="spinner-border spinner-border-sm" style={{ color: '#8B4513' }} role="status">
                      <span className="visually-hidden">Lädt...</span>
                    </div>
                  </div>
                ) : (
                  <>
                    {assignedLabels.length > 0 && (
                      <div className="mb-2">
                        <small className="text-muted d-block mb-1">Zugewiesen:</small>
                        <div className="d-flex flex-wrap gap-2">
                          {assignedLabels.map((label) => (
                            <span
                              key={label.id}
                              className="badge"
                              style={{ 
                                backgroundColor: '#2E7D32',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                                padding: '0.25rem 0.5rem'
                              }}
                              onClick={() => toggleLabel(label.id)}
                              title="Klicken zum Entfernen"
                            >
                              {label.name} <XLg size={10} />
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {unassignedLabels.length > 0 && (
                      <div>
                        <small className="text-muted d-block mb-1">Verfügbar:</small>
                        <div className="d-flex flex-wrap gap-2">
                          {unassignedLabels.map((label) => (
                            <span
                              key={label.id}
                              className="badge"
                              style={{ 
                                backgroundColor: '#9E9E9E',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                                padding: '0.25rem 0.5rem'
                              }}
                              onClick={() => toggleLabel(label.id)}
                              title="Klicken zum Hinzufügen"
                            >
                              {label.name} <PlusLg size={10} />
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {availableLabels.length === 0 && (
                      <div className="text-muted small">
                        Keine Labels verfügbar.
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="form-check form-switch">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="isActive"
                  checked={formData.isActive}
                  onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                  style={{
                    backgroundColor: formData.isActive ? '#2E7D32' : '',
                    borderColor: '#2E7D32',
                  }}
                />
                <label className="form-check-label" htmlFor="isActive">
                  aktiv
                </label>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Abbrechen
              </button>
              <button type="submit" className="btn" style={{ backgroundColor: '#8B4513', color: 'white' }}>
                Speichern
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};