import React, { useState, useEffect } from 'react';
import { Star, InfoCircle, StarFill } from 'react-bootstrap-icons';
import { useApi } from '../../../hooks/useApi';
import TapirButton from '../../../components/TapirButton';
import { BakeryApi } from '../../../api-client';
import type { BreadList, BreadContent, BreadLabel } from '../../../api-client/models';
import { PreferredBreadsModal } from '../modals/PreferredBreadsModal';
import { CompactBreadCard } from './CompactBreadCard';
import '../../styles/bakery_styles.css';


interface ChoosePreferredBreadsCardProps {
  memberId: string;
  csrfToken: string;
}
const MAX_PREFERRED_BREADS = 3;

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

  const loadData = () => {
    setLoading(true);
    bakeryApi.bakeryBreadsListList({ isActive: true })
      .then((breadsData) => {
        setAllBreads(breadsData);
        return Promise.all([
          bakeryApi.bakeryLabelsList(),
          Promise.all(
            breadsData.map((bread) =>
              bakeryApi.bakeryBreadsListContentsList({ id: bread.id! })
                .then((contents) => ({ breadId: bread.id, contents }))
                .catch(() => ({ breadId: bread.id, contents: [] as BreadContent[] }))
            )
          ),
          bakeryApi.bakeryPreferredBreadsList({ memberId }),
        ] as const);
      })
      .then(([labels, contentsResults, preferredData]) => {
        const labelMapping = labels.reduce((acc, label) => {
          if (label.id) {
            acc[label.id] = label;
          }
          return acc;
        }, {} as { [labelId: string]: BreadLabel });
        setLabelsMap(labelMapping);

        const map: { [breadId: string]: BreadContent[] } = {};
        contentsResults.forEach(({ breadId, contents }) => {
          map[breadId!] = [...contents].sort((a, b) => Number(b.amount) - Number(a.amount));
        });
        setContentsMap(map);

        if (preferredData.length > 0 && preferredData[0].breads) {
          setPreferredBreadIds(new Set(preferredData[0].breads));
        }
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
      })
      .finally(() => {
        setLoading(false);
      });
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
          className="card-header header-darkbrown-on-sahara border-bakery-primary"
          style={{ borderBottom: '1px solid var(--bakery-primary)' }}
        >
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0 text-bakery-primary-darker">
              <StarFill size={20} className="me-2 icon-bakery-gold" />
              Deine Lieblingsbrote
            </h5>
           
            <TapirButton
              variant=""
              className="dark-brown-button"
              size="sm"
              icon="star"
              text={preferredBreads.length > 0 ? 'Bearbeiten' : 'Auswählen'}
              onClick={() => setIsModalOpen(true)}
              disabled={loading}
            />
          </div>
         
        </div>

        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border spinner-bakery-primary">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : preferredBreads.length === 0 ? (
            <div className="text-center py-4">
              <Star size={48} className="mb-3 icon-bakery-primary" style={{ opacity: 0.3 }} />
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
                  <div key={bread.id} className="col-12 col-md-6 col-lg-4 d-flex">
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
          <div className="card-footer text-muted card-footer-bakery-cream">
          
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