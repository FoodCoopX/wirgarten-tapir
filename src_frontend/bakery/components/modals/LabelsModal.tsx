import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { labelsApi, breadsApi } from '../../types/client';
import type { Label } from '../../types/api';

interface Bread {
  id: string;
  name: string;
  labels?: string[];
}

interface BreadLabelsModalProps {
  bread: Bread;
  onClose: () => void;
  onUpdate?: () => void;
}

export const LabelsModal: React.FC<BreadLabelsModalProps> = ({ bread, onClose, onUpdate }) => {
  const [availableLabels, setAvailableLabels] = useState<Label[]>([]);
  const [assignedLabelIds, setAssignedLabelIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [bread.id]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [breadData, labelsData] = await Promise.all([
        breadsApi.get(bread.id),
        labelsApi.list()
      ]);

      // Ensure we're getting just the IDs as strings
      const labelIds = Array.isArray(breadData.labels) 
        ? breadData.labels.map(label => typeof label === 'object' ? label.id : String(label))
        : [];
      
      const activeLabels = labelsData.filter(label => label.is_active);
      
      setAssignedLabelIds(labelIds);
      setAvailableLabels(activeLabels);
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

const handleToggleLabel = async (labelId: string) => { // ← Changed from number
    const newLabelIds = assignedLabelIds.includes(labelId)
      ? assignedLabelIds.filter(id => id !== labelId)
      : [...assignedLabelIds, labelId];

    try {
      // Send only the array of label IDs (strings)
      await breadsApi.update(bread.id, { labels: newLabelIds });
      setAssignedLabelIds(newLabelIds);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Failed to update labels:', error);
      alert('Fehler beim Aktualisieren der Labels');
    }
  };
  const modalContent = (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          zIndex: 9999,
        }}
        onClick={onClose}
      />

      {/* Modal Content */}
      <div
        style={{
          position: 'relative',
          zIndex: 10000,
          width: '100%',
          maxWidth: '600px',
          maxHeight: '85vh',
          overflow: 'auto',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}
      >
        <div 
          className="p-3 d-flex justify-content-between align-items-center" 
          style={{ backgroundColor: '#F5E6D3', color: '#8B4513', borderRadius: '8px 8px 0 0' }}
        >
          <h5 className="mb-0">
            <span className="material-icons me-2" style={{ fontSize: '20px', verticalAlign: 'middle' }}>label</span>
            Labels: {bread.name}
          </h5>
          <button type="button" className="btn-close" onClick={onClose}></button>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" style={{ color: '#8B4513' }} role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : (
            <>
              {availableLabels.length === 0 ? (
                <div className="text-center text-muted py-4">
                  Keine Labels verfügbar.
                </div>
              ) : (
                <div className="list-group">
                  {availableLabels.map((label) => {
                    const isAssigned = assignedLabelIds.includes(label.id);
                    return (
                      <div 
                        key={label.id} 
                        className="list-group-item d-flex justify-content-between align-items-center"
                        style={{ 
                          cursor: 'pointer',
                          backgroundColor: isAssigned ? '#F5E6D3' : 'white'
                        }}
                        onClick={() => handleToggleLabel(label.id)}
                      >
                        <div className="flex-grow-1">
                          <strong>{label.name}</strong>
                          {label.description && (
                            <div className="text-muted small">{label.description}</div>
                          )}
                        </div>
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            checked={isAssigned}
                            onChange={() => handleToggleLabel(label.id)}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                  backgroundColor: isAssigned ? '#8B6F47' : '',
                                  borderColor: isAssigned ? '#8B6F47' : '',
                                  cursor: 'pointer',
                                }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {assignedLabelIds.length > 0 && (
                <div className="mt-3">
                  <strong>Zugewiesene Labels: {assignedLabelIds.length}</strong>
                </div>
              )}
            </>
          )}
        </div>

        <div className="p-3 border-top d-flex justify-content-end" style={{ borderRadius: '0 0 8px 8px' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Schließen
          </button>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};