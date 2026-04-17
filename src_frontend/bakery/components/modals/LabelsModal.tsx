import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadLabel, BreadList } from '../../../api-client/models';

interface BreadLabelsModalProps {
  bread: BreadList;
  csrfToken: string;
  onClose: () => void;
  onUpdate?: () => void;
}

export const LabelsModal: React.FC<BreadLabelsModalProps> = ({ bread, csrfToken, onClose, onUpdate }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [availableLabels, setAvailableLabels] = useState<BreadLabel[]>([]);
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

  const loadData = () => {
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadsListRetrieve({ id: bread.id! }),
      bakeryApi.bakeryLabelsList()
    ])
      .then(([breadData, labelsData]) => {
        // Extract label IDs — handle both string[] and object[] formats
        const labelIds: string[] = Array.isArray(breadData.labels) 
          ? breadData.labels.map((label: any) => typeof label === 'object' ? label.id : String(label))
          : [];
        

        const activeLabels = labelsData.filter(label => label.isActive !== false);
        
        setAssignedLabelIds(labelIds);
        setAvailableLabels(activeLabels);
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
        alert('Fehler beim Laden der Daten');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleToggleLabel = (labelId: string) => {
    const isAssigned = assignedLabelIds.includes(labelId);
    const newLabelIds = isAssigned
      ? assignedLabelIds.filter(id => id !== labelId)
      : [...assignedLabelIds, labelId];

    // Optimistic update
    setAssignedLabelIds(newLabelIds);

    bakeryApi.bakeryBreadsListPartialUpdate({
      id: bread.id!,
      patchedBreadListRequest: { labels: newLabelIds }
    })
      .then(() => {
        if (onUpdate) onUpdate();
      })
      .catch((error) => {
        // Revert on failure
        setAssignedLabelIds(assignedLabelIds);
        console.error('Failed to update labels:', error);
        alert('Fehler beim Aktualisieren der Labels');
      });
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
          className="p-3 d-flex justify-content-between align-items-center header-darkbrown-on-sahara" 
          style={{ borderRadius: '8px 8px 0 0' }}
        >
          <h5 className="mb-0 d-inline-flex align-items-center gap-2">
            
            Labels: {bread.name}
          </h5>
          <button type="button" className="btn-close" onClick={onClose}></button>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-bakery-primary-dark" role="status">
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
                    const isAssigned = assignedLabelIds.includes(label.id!);
                    return (
                      <div 
                        key={label.id} 
                        className="list-group-item d-flex justify-content-between align-items-center"
                        style={{ 
                          cursor: 'pointer',
                          backgroundColor: isAssigned ? 'var(--bakery-table-header)' : 'white'
                        }}
                        onClick={() => handleToggleLabel(label.id!)}
                      >
                        <div className="flex-grow-1">
                          <strong>{label.name}</strong>
                        </div>
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            role="switch"
                            checked={isAssigned}
                            onChange={() => handleToggleLabel(label.id!)}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              backgroundColor: isAssigned ? 'var(--bakery-primary-dark)' : '',
                              borderColor: isAssigned ? 'var(--bakery-primary-dark)' : '',
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
          <button type="button" className="btn btn-secondary dark-brown-button" onClick={onClose}>
            Speichern & Schließen
          </button>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};