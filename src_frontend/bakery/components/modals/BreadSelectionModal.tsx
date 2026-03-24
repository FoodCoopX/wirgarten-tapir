import React, { useState, useEffect } from 'react';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';
import { SingleBreadCard } from '../cards';
import '../../styles/bakery_styles.css';

interface BreadSelectionModalProps {
  breads: BreadList[];
  contentsMap: { [breadId: string]: BreadContent[] };
  pickupLocationId: string;
  pickupLocationName: string;
  selectedWeek: number;
  selectedYear: number;
  currentBreadId?: string | null;
  onSelect: (breadId: string) => void;
  onClose: () => void;
  csrfToken: string;
}

export const BreadSelectionModal: React.FC<BreadSelectionModalProps> = ({
  breads: initialBreads,
  contentsMap,
  pickupLocationId,
  pickupLocationName,
  selectedWeek,
  selectedYear,
  currentBreadId,
  onSelect,
  onClose,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [availableBreads, setAvailableBreads] = useState<BreadList[]>([]);
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [pickupLocationId, selectedWeek, selectedYear]);

  const loadData = async () => {
    setLoading(true);
    try {
      const breadsWithCapacity = await bakeryApi.bakeryBreadsListList({
        isActive: true,
        pickupLocationId,
        year: selectedYear,
        week: selectedWeek,
      });
      
      const labels = await bakeryApi.bakeryLabelsList();
      
      const labelMapping = labels.reduce((acc, label) => {
        if (label.id) {
          acc[label.id] = label;
        }
        return acc;
      }, {} as { [labelId: string]: BreadLabel });
      
      setLabelsMap(labelMapping);
      setAvailableBreads(breadsWithCapacity);
    } catch (error) {
      console.error('Failed to load data:', error);
      setAvailableBreads([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div 
        className="modal-backdrop fade show" 
        onClick={onClose}
        style={{ zIndex: 1050 }}
      />

      <div 
        className="modal fade show d-block" 
        tabIndex={-1}
        style={{ zIndex: 1055 }}
      >
        <div className="modal-dialog modal-xl modal-dialog-scrollable">
          <div className="modal-content">
            <div 
              className="modal-header header-darkbrown-on-sahara" 
            >
              <h5 className="modal-title">
                Brot auswählen für {pickupLocationName}
              </h5>
              <button 
                type="button" 
                className="btn-close" 
                onClick={onClose}
              />
            </div>

            <div className="modal-body modal-body-bakery">
              {loading ? (
                <div className="text-center py-5">
                  <div className="spinner-border spinner-bakery" />
                  <p className="mt-2 text-muted">Lade verfügbare Brote...</p>
                </div>
              ) : (
                <>
                  <div className="alert alert-info mb-4">
                    <strong>KW {selectedWeek}/{selectedYear}</strong> - Station: {pickupLocationName}
                    <br />
                    <small>{availableBreads.length} Brotsorte{availableBreads.length !== 1 ? 'n' : ''} verfügbar</small>
                  </div>

                  {availableBreads.length === 0 ? (
                    <div className="alert alert-warning">
                      <strong>Keine Brote verfügbar</strong>
                      <p className="mb-0">
                        Für diese Abholstation und Woche sind noch keine Brote mit verfügbarer Kapazität vorhanden.
                      </p>
                    </div>
                  ) : (
                    <div className="d-flex flex-wrap gap-3">
                      {availableBreads.map(bread => {
                        const contents = contentsMap[bread.id!] || [];
                        const breadLabels = (bread.labels || [])
                          .map(labelId => labelsMap[labelId])
                          .filter(Boolean);
                        const isSelected = bread.id === currentBreadId;

                        return (
                          <SingleBreadCard
                            key={bread.id}
                            bread={bread}
                            contents={contents}
                            labels={breadLabels}
                            isSelected={isSelected}
                            onClick={() => onSelect(bread.id!)}
                          />
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};