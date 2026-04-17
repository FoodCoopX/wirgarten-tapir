import React, { useState, useEffect } from 'react';
import { Modal } from 'react-bootstrap';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { handleRequestError } from '../../../utils/handleRequestError';
import type { BreadLabel, BreadList } from '../../../api-client/models';
import TapirButton from '../../../components/TapirButton';

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
        handleRequestError(error, 'Fehler beim Laden der Daten');
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
        handleRequestError(error, 'Fehler beim Aktualisieren der Labels');
      });
  };

  return (
    <Modal show onHide={onClose} centered>
      <Modal.Header closeButton className="header-darkbrown-on-sahara">
        <Modal.Title>Labels: {bread.name}</Modal.Title>
      </Modal.Header>

      <Modal.Body>
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
      </Modal.Body>

      <Modal.Footer>
        <TapirButton variant="" className="dark-brown-button" text="Speichern & Schließen" icon="save" onClick={onClose} />
      </Modal.Footer>
    </Modal>
  );
};