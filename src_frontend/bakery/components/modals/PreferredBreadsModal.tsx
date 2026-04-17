import React, { useState, useEffect } from 'react';
import { InfoCircle, StarFill } from 'react-bootstrap-icons';
import { useApi } from '../../../hooks/useApi';
import { BakeryApi } from '../../../api-client';
import type { BreadList, BreadLabel, BreadContent } from '../../../api-client/models';
import { SingleBreadCard } from '../cards';
import '../../styles/bakery_styles.css';

interface PreferredBreadsModalProps {
  isOpen: boolean;
  onClose: () => void;
  memberId: string;
  csrfToken: string;
}

const MAX_PREFERRED_BREADS = 3;

export const PreferredBreadsModal: React.FC<PreferredBreadsModalProps> = ({
  isOpen,
  onClose,
  memberId,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>({});
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [selectedBreadIds, setSelectedBreadIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, memberId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !saving) {
        e.preventDefault();
        handleSave();
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, saving, selectedBreadIds]);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadsListList({}),
      bakeryApi.bakeryPreferredBreadsList({ memberId }),
      bakeryApi.bakeryLabelsList(),
      bakeryApi.bakeryBreadcontentsList(),
    ])
      .then(([breadsData, preferredData, labels, contents]) => {
        setBreads(breadsData.filter(b => b.isActive !== false));

        const labelMapping = labels.reduce((acc, label) => {
          if (label.id) {
            acc[label.id] = label;
          }
          return acc;
        }, {} as { [labelId: string]: BreadLabel });
        setLabelsMap(labelMapping);

        const contentMapping = contents.reduce((acc, content) => {
          const breadId = content.bread;
          if (breadId) {
            if (!acc[breadId]) {
              acc[breadId] = [];
            }
            acc[breadId].push(content);
          }
          return acc;
        }, {} as { [breadId: string]: BreadContent[] });
        setContentsMap(contentMapping);


        if (preferredData.length > 0 && preferredData[0].breads) {
          setSelectedBreadIds(new Set(preferredData[0].breads));
        }
      })
      .catch((error) => {
        console.error('Failed to load breads:', error);
        alert('Fehler beim Laden der Brote');
      })
      .finally(() => {
        setLoading(false);
      });
  };

   const toggleBread = (breadId: string) => {
    const newSelected = new Set(selectedBreadIds);
    
    if (newSelected.has(breadId)) {
      newSelected.delete(breadId);
    } else {
      // If at limit, remove the first selected bread to make room
      if (newSelected.size >= MAX_PREFERRED_BREADS) {
        const firstBreadId = Array.from(newSelected)[0];
        newSelected.delete(firstBreadId);
      }
      newSelected.add(breadId);
    }
    
    setSelectedBreadIds(newSelected);
  };
  const handleSave = () => {
    setSaving(true);
    bakeryApi.bakeryPreferredBreadsBulkUpdateCreate({
      id: memberId,
      preferredBreadsBulkUpdateRequest: {
        breads: Array.from(selectedBreadIds),
      },
    })
      .then(() => {
        onClose();
      })
      .catch((error) => {
        console.error('Failed to save preferred breads:', error);
        alert('Fehler beim Speichern der Lieblingsbrote');
      })
      .finally(() => {
        setSaving(false);
      });
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="modal-backdrop fade show"
        onClick={onClose}
        style={{ zIndex: 1040 }}
      />
      <div
        className="modal fade show d-block"
        tabIndex={-1}
        style={{ zIndex: 1050 }}
      >
        <div className="modal-dialog modal-xl modal-dialog-scrollable">
          <div className="modal-content">
            <div
              className="modal-header header-white-on-middle-brown"
            >
              <h5 className="modal-title">
                <StarFill size={20} className="me-2" />
                Lieblingsbrote auswählen
              </h5>
              <button
                type="button"
                className="btn-close btn-close-white"
                onClick={onClose}
                disabled={saving}
              />
            </div>

            <div className="modal-body p-4">
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border spinner-bakery-primary" />
                  <p className="mt-2 text-muted">Lade Brote...</p>
                </div>
              ) : breads.length === 0 ? (
                <div className="alert alert-info d-flex align-items-center" role="alert">
                  <InfoCircle size={20} className="me-2" />
                  Keine Brote verfügbar.
                </div>
              ) : (
                <>
                  <div className="alert alert-light d-flex align-items-start mb-4" role="alert">
                    <InfoCircle size={20} className="me-2 mt-1 icon-bakery-primary-darker" style={{ color: 'var(--bakery-brown-medium)' }} />
                    <div>
                      <strong>Wähle bis zu {MAX_PREFERRED_BREADS} Lieblingsbrote aus</strong>
                      <p className="mb-0 small text-muted">
                        Wir versuchen die Abhol-Orte so mit möglichst vielen Lieblingsbroten zu bestücken.
                      </p>
                    </div>
                  </div>

                  <div className="d-flex flex-wrap gap-3">
                    {breads.map((bread) => {
                      const isSelected = selectedBreadIds.has(bread.id!);
                      const breadLabels = (bread.labels || [])
                        .map(labelId => labelsMap[labelId])
                        .filter(Boolean);

                      const breadContents = contentsMap[bread.id!] || [];


                      return (
                        <SingleBreadCard
                          key={bread.id}
                          bread={bread}
                          contents={breadContents}
                          labels={breadLabels}
                          isPreferred={isSelected}
                          onClick={() => toggleBread(bread.id!)}
                          footerText={isSelected ? 'Lieblingsbrot' : 'Auswählen'}
                        />
                      );
                    })}
                  </div>
                </>
              )}
            </div>

            <div className="modal-footer">
              <div className="me-auto text-muted small">
                {selectedBreadIds.size} / {MAX_PREFERRED_BREADS} {selectedBreadIds.size === 1 ? 'Brot' : 'Brote'} ausgewählt
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={saving}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="btn dark-brown-button"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" />
                    Speichert...
                  </>
                ) : (
                  'Speichern'
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};