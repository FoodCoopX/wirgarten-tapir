import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { PlusLg, XLg, Trash } from 'react-bootstrap-icons';
import type { BreadLabel, BreadList, BreadListRequest } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

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
    piecesPerStoveLayer: [],
    oneBatchCanBeBakedInMoreThanOneStove: false,
    minPieces: undefined,
    maxPieces: undefined,
    minRemainingPieces: undefined,
  });
  const [availableLabels, setAvailableLabels] = useState<BreadLabel[]>([]);
  const [loading, setLoading] = useState(true);
  
  // For pieces per stove layer input
  const [piecesInput, setPiecesInput] = useState('');

  useEffect(() => {
    loadLabels();
    if (bread) {
      const labelIds = (bread.labels || [])
        .map(label => typeof label === 'object' ? (label as any).id : label);

      setFormData({
        name: bread.name,
        description: bread.description || '',
        weight: String(bread.weight),
        isActive: bread.isActive,
        labels: labelIds,
        piecesPerStoveLayer: bread.piecesPerStoveLayer || [],
        oneBatchCanBeBakedInMoreThanOneStove: bread.oneBatchCanBeBakedInMoreThanOneStove || false,
        minPieces: bread.minPieces,
        maxPieces: bread.maxPieces,
        minRemainingPieces: bread.minRemainingPieces,
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
      labels: prev.labels!.includes(labelId)
        ? prev.labels!.filter(id => id !== labelId)
        : [...prev.labels!, labelId]
    }));
  };

  const addPiecesPerLayer = () => {
    const value = parseInt(piecesInput);
    if (!isNaN(value) && value > 0 && !formData.piecesPerStoveLayer?.includes(value)) {
      setFormData(prev => ({
        ...prev,
        piecesPerStoveLayer: [...(prev.piecesPerStoveLayer || []), value].sort((a, b) => a - b)
      }));
      setPiecesInput('');
    }
  };

  const removePiecesPerLayer = (value: number) => {
    setFormData(prev => ({
      ...prev,
      piecesPerStoveLayer: (prev.piecesPerStoveLayer || []).filter((v): v is number => typeof v === 'number' && v !== value)
    }));
  };

  const assignedLabels = availableLabels.filter(label => formData.labels!.includes(label.id!));
  const unassignedLabels = availableLabels.filter(label => !formData.labels!.includes(label.id!));

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header header-darkbrown-on-sahara">
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
                  {formData.labels!.length > 0 && (
                    <span className="badge bg-success ms-2">{formData.labels!.length}</span>
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
                              onClick={() => toggleLabel(label.id!)}
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
                              onClick={() => toggleLabel(label.id!)}
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

              <div className="form-check form-switch mb-3">
                <input
                  className="form-check-input form-switch-bakery"
                  type="checkbox"
                  id="isActive"
                  checked={formData.isActive}
                  onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                  
                />
                <label className="form-check-label" htmlFor="isActive">
                  aktiv
                </label>
              </div>

              {/* Baking Details Section */}
              <div className="border rounded p-3" style={{ backgroundColor: '#F8F9FA' }}>
                
                  <h6 className="mb-0" style={{ color: '#8B4513' }}>
                    Back-Details 
                  </h6>
                
                  <div className="mt-3">
                    {/* Pieces per stove layer */}
                    <div className="mb-3">
                      <label className="form-label fw-bold small">
                        Stücke pro Etage
                      </label>
                        <span className="text-muted d-block" style={{ fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                        Mögliche Anzahl Brote, die pro Etage gebacken werden können. <br/>Um mehrere Zahlen einzugeben bzw. um zu speichern, bitte auf "+" klicken oder "Enter" drücken.
                      </span>
                      <div className="input-group input-group-sm mb-2">
                        <input
                          type="number"
                          className="form-control"
                          value={piecesInput}
                          onChange={(e) => setPiecesInput(e.target.value)}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault();
                              addPiecesPerLayer();
                            }
                          }}
                          placeholder="Anzahl eingeben..."
                          min="1"
                        />
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={addPiecesPerLayer}
                        >
                          <PlusLg size={14} />
                        </button>
                      </div>
                       <div className="d-flex flex-wrap gap-2">
                        {(formData.piecesPerStoveLayer || [])
                          .filter((v): v is number => typeof v === 'number')
                          .map((value: number) => (
                          <span
                            key={value}
                            className="badge bg-secondary"
                            style={{ fontSize: '0.85rem', cursor: 'pointer' }}
                            onClick={() => removePiecesPerLayer(value)}
                            title="Klicken zum Entfernen"
                          >
                            {value} <Trash size={12} className="ms-1" />
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Can be baked in multiple stoves */}
                    <div className="form-check form-switch mb-3">
                      <input
                        className="form-check-input form-switch-bakery"
                        type="checkbox"
                        id="oneBatchCanBeBakedInMoreThanOneStove"
                        checked={formData.oneBatchCanBeBakedInMoreThanOneStove}
                        onChange={(e) => setFormData({ ...formData, oneBatchCanBeBakedInMoreThanOneStove: e.target.checked })}
                      />
                      <label className="form-check-label small" htmlFor="oneBatchCanBeBakedInMoreThanOneStove">
                        Ein Teig kann in mehreren Ofengängen gebacken werden
                        <span className="text-muted d-block" style={{ fontSize: '0.75rem' }}>
                          (z.B. wenn der Teig zwischendurch gekühlt werden kann)
                        </span>
                      </label>
                    </div>

                    {/* Min/Max pieces */}
                    <div className="row">
                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="minPieces" className="form-label fw-bold small">
                            Min. Stücke
                          </label>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            id="minPieces"
                            value={formData.minPieces || ''}
                            onChange={(e) => setFormData({ 
                              ...formData, 
                              minPieces: e.target.value ? parseInt(e.target.value) : undefined 
                            })}
                            min="0"
                            placeholder="z.B. 10"
                          />
                          <small className="text-muted">
                            Mindestanzahl pro Backtag
                          </small>
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="maxPieces" className="form-label fw-bold small">
                            Max. Stücke
                          </label>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            id="maxPieces"
                            value={formData.maxPieces || ''}
                            onChange={(e) => setFormData({ 
                              ...formData, 
                              maxPieces: e.target.value ? parseInt(e.target.value) : undefined 
                            })}
                            min="0"
                            placeholder="z.B. 50"
                          />
                          <small className="text-muted">
                            Maximalanzahl pro Backtag
                          </small>
                        </div>
                      </div>

                      <div className="col-md-4">
                        <div className="mb-3">
                          <label htmlFor="minRemainingPieces" className="form-label fw-bold small">
                            Min. Übrig
                          </label>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            id="minRemainingPieces"
                            value={formData.minRemainingPieces || ''}
                            onChange={(e) => setFormData({ 
                              ...formData, 
                              minRemainingPieces: e.target.value ? parseInt(e.target.value) : undefined 
                            })}
                            min="0"
                            placeholder="z.B. 5"
                          />
                          <small className="text-muted">
                            Für Laufkundschaft
                          </small>
                        </div>
                      </div>
                    </div>
                  </div>
                
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Abbrechen
              </button>
              <button type="submit" className="btn dark-brown-button">
                Speichern & Schließen
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};