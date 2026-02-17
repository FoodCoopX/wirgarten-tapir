import React, { useState, useEffect } from 'react';
import { labelsApi } from '../../types/client';
import type { Label } from '../../types/api';

interface Bread {
  id: string;
  name: string;
  description: string;
  weight: number;
  picture?: string;
  is_active: boolean;
  labels: string[];
}

interface BreadModalProps {
  bread: Bread | null;
  onSave: (bread: Partial<Bread>) => void;
  onClose: () => void;
}

export const BreadModal: React.FC<BreadModalProps> = ({ bread, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    weight: 500,
    is_active: true,
    labels: [] as string[],
  });
  const [availableLabels, setAvailableLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLabels();
    if (bread) {
      // Handle both string IDs and full label objects
      const labelIds = Array.isArray(bread.labels)
        ? bread.labels.map(label => typeof label === 'object' ? label.id : String(label))
        : [];

      setFormData({
        name: bread.name,
        description: bread.description,
        weight: bread.weight,
        is_active: bread.is_active,
        labels: labelIds,
      });
    }
  }, [bread]);

  const loadLabels = async () => {
    setLoading(true);
    try {
      const data = await labelsApi.list();
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
                      onChange={(e) => setFormData({ ...formData, weight: Number(e.target.value) })}
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
                    {/* Assigned Labels */}
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
                              {label.name}
                              <span className="ms-1 material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>
                                close
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Unassigned Labels */}
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
                              {label.name}
                              <span className="ms-1 material-icons" style={{ fontSize: '12px', verticalAlign: 'middle' }}>
                                add
                              </span>
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
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                style={{
                    backgroundColor: formData.is_active ? '#2E7D32' : '',
                    borderColor: '#2E7D32',
                  }}
                />
                <label className="form-check-label" htmlFor="is_active">
                  aktiv
                </label>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Abbrechen
              </button>
              <button type="submit" className="btn" style={{ backgroundColor: '#8B4513', color: 'white' }}>
                <span className="material-icons me-2" style={{ fontSize: '16px' }}>save</span>
                Speichern
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};