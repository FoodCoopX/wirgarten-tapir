import React, { useState, useEffect } from 'react';
import { Star, StarFill } from 'react-bootstrap-icons';
import { useApi } from '../../../hooks/useApi';
import { BakeryApi } from '../../../api-client';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';
import { PreferredBreadsModal } from '../modals/PreferredBreadsModal';
import { CompactBreadCard } from './CompactBreadCard';

interface ChoosePreferredBreadsCardProps {
  memberId: string;
  csrfToken: string;
}

export const ChoosePreferredBreadsCard: React.FC<ChoosePreferredBreadsCardProps> = ({ 
  memberId, 
  csrfToken 
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [allBreads, setAllBreads] = useState<BreadList[]>([]);
  const [preferredBreadIds, setPreferredBreadIds] = useState<Set<string>>(new Set());
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [labelsMap, setLabelsMap] = useState<{ [labelId: string]: BreadLabel }>({});
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load breads
      const breadsData = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setAllBreads(breadsData);

      // Load labels
      const labels = await bakeryApi.bakeryLabelsList();
      const labelMapping = labels.reduce((acc, label) => {
        if (label.id) {
          acc[label.id] = label;
        }
        return acc;
      }, {} as { [labelId: string]: BreadLabel });
      setLabelsMap(labelMapping);

      // Load contents for all breads
      const contentsResults = await Promise.all(
        breadsData.map(async (bread) => {
          try {
            const contents = await bakeryApi.bakeryBreadsListContentsList({ id: bread.id! });
            return { breadId: bread.id, contents };
          } catch {
            return { breadId: bread.id, contents: [] };
          }
        })
      );

      const map: { [breadId: string]: BreadContent[] } = {};
      contentsResults.forEach(({ breadId, contents }) => {
        map[breadId!] = [...contents].sort((a, b) => Number(b.amount) - Number(a.amount));
      });
      setContentsMap(map);

      // Load preferred breads
      const preferredData = await bakeryApi.bakeryPreferredBreadsList({ memberId });
      if (preferredData.length > 0 && preferredData[0].breads) {
        setPreferredBreadIds(new Set(preferredData[0].breads));
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    loadData(); // Reload data after modal closes
  };

  const preferredBreads = allBreads.filter(bread => preferredBreadIds.has(bread.id!));

  return (
    <>
      <div className="card">
        <div 
          className="card-header"
          style={{ backgroundColor: '#F5E6D3', borderBottom: '1px solid #D4A574' }}
        >
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0" style={{ color: '#8B4513' }}>
              <StarFill size={20} className="me-2" style={{ color: '#FFD700' }} />
              Deine Lieblingsbrote
            </h5>
            <button
              className="btn btn-sm"
              style={{ backgroundColor: '#8B6F47', color: 'white' }}
              onClick={() => setIsModalOpen(true)}
              disabled={loading}
            >
              <Star size={16} className="me-1" />
              {preferredBreads.length > 0 ? 'Bearbeiten' : 'Auswählen'}
            </button>
          </div>
        </div>

        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" style={{ color: '#D4A574' }}>
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : preferredBreads.length === 0 ? (
            <div className="text-center py-4">
              <Star size={48} className="mb-3" style={{ color: '#D4A574', opacity: 0.3 }} />
              <p className="text-muted mb-0">
                Du hast noch keine Lieblingsbrote ausgewählt.
              </p>
              <p className="text-muted small">
                Klicke auf "Auswählen", um deine Favoriten festzulegen.
              </p>
            </div>
          ) : (
            <div className="row g-3">
              {preferredBreads.map((bread) => {
                const breadLabels = (bread.labels || [])
                  .map(labelId => labelsMap[labelId])
                  .filter(Boolean);
                const contents = contentsMap[bread.id!] || [];

                return (
                  <div key={bread.id} className="col-12 col-md-6 col-lg-4">
                    <CompactBreadCard
                      bread={bread}
                      contents={contents}
                      labels={breadLabels}
                      showActions={false}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {preferredBreads.length > 0 && (
          <div className="card-footer text-muted" style={{ backgroundColor: '#F5E6D3' }}>
            <small>
              {preferredBreads.length} {preferredBreads.length === 1 ? 'Lieblingsbrot' : 'Lieblingsbrote'} ausgewählt
            </small>
          </div>
        )}
      </div>

      <PreferredBreadsModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        memberId={memberId}
        csrfToken={csrfToken}
      />
    </>
  );
};