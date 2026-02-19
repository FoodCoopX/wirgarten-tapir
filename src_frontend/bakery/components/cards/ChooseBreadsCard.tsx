import React, { useState, useEffect } from 'react';
import { EggFried, Plus, Dash } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import { BrownCircleButton } from '../BrownCircleButton';
import type { BreadList, BreadContent, Subscription } from '../../../api-client/models';

interface ChooseBreadsCardProps {
  memberId: string;
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
  csrfToken: string;
}

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({
  memberId,
  year,
  deliveryWeek,
  deliveryDay,
  csrfToken,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);

  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [selectedBreads, setSelectedBreads] = useState<string[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [memberId, year, deliveryWeek, deliveryDay]);

  const loadData = async () => {
    try {
      const allBreads = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setBreads(allBreads);

      const contentsResults = await Promise.all(
        allBreads.map(async (bread) => {
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

      // TODO: Load subscription and selected breads from your backend
      // setSubscription(...);
      // setSelectedBreads(...);

      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const maxBreads = subscription?.quantity || 0;
  const remainingSlots = maxBreads - selectedBreads.length;

  const handleAddBread = async (breadId: string) => {
    if (!subscription || remainingSlots <= 0) return;
    setSaving(true);
    try {
      // TODO: Save to backend
      setSelectedBreads([...selectedBreads, breadId]);
    } catch (error) {
      setSelectedBreads(selectedBreads);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveBread = async (breadId: string) => {
    if (!subscription) return;
    const idx = selectedBreads.indexOf(breadId);
    if (idx === -1) return;
    setSaving(true);
    try {
      // TODO: Remove from backend
      const newSelection = [...selectedBreads];
      newSelection.splice(idx, 1);
      setSelectedBreads(newSelection);
    } catch (error) {
      setSelectedBreads(selectedBreads);
    } finally {
      setSaving(false);
    }
  };

  const getQuantityForBread = (breadId: string) => {
    return selectedBreads.filter(id => id === breadId).length;
  };

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border" style={{ color: '#D4A574' }} role="status">
          <span className="visually-hidden">Lädt...</span>
        </div>
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className="alert alert-warning">
        <p className="mb-0">Keine aktive Subscription gefunden.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="alert alert-info mb-3">
        <strong>{selectedBreads.length} / {maxBreads}</strong> Brote ausgewählt
        {remainingSlots > 0 && ` (noch ${remainingSlots} verfügbar)`}
      </div>
      <div className="d-flex flex-wrap gap-3">
        {breads.map(bread => {
          const qty = getQuantityForBread(bread.id!);
          const contents = contentsMap[bread.id!] || [];

          return (
            <div key={bread.id} style={{ width: '280px', flex: '0 0 280px' }}>
              <div
                className="card h-100 shadow-sm"
                style={{
                  border: qty > 0 ? '2px solid #8B4513' : '1px solid #dee2e6',
                  opacity: remainingSlots === 0 && qty === 0 ? 0.6 : 1,
                }}
              >
                {bread.picture ? (
                  <img
                    src={bread.picture}
                    alt={bread.name}
                    className="card-img-top"
                    style={{ height: '180px', objectFit: 'cover' }}
                  />
                ) : (
                  <div
                    className="d-flex align-items-center justify-content-center"
                    style={{ height: '180px', backgroundColor: '#F5E6D3' }}
                  >
                    <EggFried size={48} style={{ color: '#D4A574' }} />
                  </div>
                )}

                <div className="card-body d-flex flex-column">
                  <h6 className="card-title mb-0" style={{ color: '#8B4513' }}>
                    {bread.name}
                  </h6>

                  {bread.weight && (
                    <small className="text-muted mb-2">{Number(bread.weight).toFixed(0)}g</small>
                  )}

                  {bread.labels && bread.labels.length > 0 && (
                    <div className="mb-2">
                      {bread.labels.map(label => (
                        <span
                          key={label.id}
                          className="badge me-1"
                          style={{ backgroundColor: '#F5E6D3', color: '#8B4513', fontSize: '0.7rem' }}
                        >
                          {label.name}
                        </span>
                      ))}
                    </div>
                  )}

                  {bread.description && (
                    <p className="card-text text-muted small mb-2">{bread.description}</p>
                  )}

                  {contents.length > 0 && (
                    <div className="mb-2" style={{ flex: 1 }}>
                      <small className="fw-bold" style={{ color: '#C4A882', fontSize: '0.7rem' }}>
                        ZUTATEN:
                      </small>
                      <br />
                      <small style={{ color: '#B8A99A', fontSize: '0.75rem' }}>
                        {contents.map(c => c.ingredientName).join(', ')}
                      </small>
                    </div>
                  )}

                 
                  <div className="d-flex align-items-center justify-content-center gap-2 mt-auto">
                    
                    <BrownCircleButton
                      active={qty > 0}
                      onClick={() => handleRemoveBread(bread.id!)}
                      disabled={qty === 0 || saving}
                    >
                      <Dash size={18} />
                    </BrownCircleButton>

                    <span
                      className="fw-bold text-center"
                      style={{ minWidth: '32px', fontSize: '1.1rem', color: qty > 0 ? '#8B4513' : '#adb5bd' }}
                    >
                      {qty}
                    </span>

                    <button
                      className="btn btn-sm rounded-circle"
                      style={{
                        width: '32px',
                        height: '32px',
                        backgroundColor: '#8B4513',
                        color: 'white',
                      }}
                      onClick={() => handleAddBread(bread.id!)}
                      disabled={remainingSlots === 0 || saving}
                    >
                      <Plus size={18} />
                    </button>
                  </div>
                </div>

                {qty > 0 && (
                  <div
                    className="card-footer text-center py-1"
                    style={{ backgroundColor: '#8B4513', color: 'white', fontSize: '0.8rem' }}
                  >
                    {qty}× ausgewählt
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};