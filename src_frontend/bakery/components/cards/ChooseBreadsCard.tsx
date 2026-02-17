import React, { useState, useEffect } from 'react';
import { BakeryApi, Configuration } from '../../api-client';
import type { BreadList, BreadContent, Subscription } from '../../api-client/models';

// Create API instance
const config = new Configuration({
  basePath: '',
});
const bakeryApi = new BakeryApi(config);

interface ChooseBreadsCardProps {
  memberId: string;
  year: number;
  deliveryWeek: number;
  deliveryDay: number;
}

export const ChooseBreadsCard: React.FC<ChooseBreadsCardProps> = ({ 
  memberId, 
  year, 
  deliveryWeek, 
  deliveryDay 
}) => {
  const [breads, setBreads] = useState<BreadList[]>([]);
  const [contentsMap, setContentsMap] = useState<{ [breadId: string]: BreadContent[] }>({});
  const [selectedBreads, setSelectedBreads] = useState<string[]>([]); // Array of bread IDs
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, [memberId, year, deliveryWeek, deliveryDay]);

  const loadData = async () => {
    try {
      // Load active breads
      const allBreads = await bakeryApi.bakeryBreadsListList({ isActive: true });
      setBreads(allBreads);

      // Load contents for each bread
      const contentsResults = await Promise.all(
        allBreads.map(async (bread) => {
          try {
            const contents = await bakeryApi.bakeryBreadsListContentsList({ id: bread.id });
            return { breadId: bread.id, contents };
          } catch {
            return { breadId: bread.id, contents: [] };
          }
        })
      );

      const map: { [breadId: string]: BreadContent[] } = {};
      contentsResults.forEach(({ breadId, contents }) => {
        map[breadId] = [...contents].sort((a, b) => Number(b.amount) - Number(a.amount));
      });
      setContentsMap(map);

      // Load member's subscription
      // Note: You'll need to check if there's a subscription API endpoint
      // For now, this is a placeholder - adjust based on your actual API
      // const subs = await subscriptionsApi.listByMember(memberId);
      // const activeSub = subs.find(s => s.is_active);
      // setSubscription(activeSub || null);

      // Load existing selections for this week
      // Note: You'll need to check if there's a bread deliveries API endpoint
      // if (activeSub) {
      //   const deliveries = await breadDeliveriesApi.list({
      //     subscription: activeSub.id,
      //     year,
      //     delivery_week: deliveryWeek,
      //     delivery_day: deliveryDay,
      //   });
      //   setSelectedBreads(deliveries.map(d => d.bread));
      // }

      setLoading(false);
    } catch (error) {
      console.error('Failed to load data:', error);
      setLoading(false);
    }
  };

  const maxBreads = subscription?.quantity || 0;
  const remainingSlots = maxBreads - selectedBreads.length;

  const handleToggleBread = async (breadId: string) => {
    if (!subscription) return;

    const isSelected = selectedBreads.includes(breadId);

    if (isSelected) {
      // Remove one instance
      const index = selectedBreads.indexOf(breadId);
      const newSelection = [...selectedBreads];
      newSelection.splice(index, 1);
      
      setSelectedBreads(newSelection);
      
      // Delete from backend
      setSaving(true);
      try {
        // Note: Adjust this based on your actual bread deliveries API
        // const deliveries = await breadDeliveriesApi.list({
        //   subscription: subscription.id,
        //   year,
        //   delivery_week: deliveryWeek,
        //   delivery_day: deliveryDay,
        //   bread: breadId,
        // });
        // if (deliveries.length > 0) {
        //   await breadDeliveriesApi.delete(deliveries[0].id);
        // }
      } catch (error) {
        console.error('Failed to remove bread:', error);
        setSelectedBreads(selectedBreads); // Revert
      } finally {
        setSaving(false);
      }
    } else {
      // Add if slots available
      if (remainingSlots <= 0) return;

      const newSelection = [...selectedBreads, breadId];
      setSelectedBreads(newSelection);

      // Save to backend
      setSaving(true);
      try {
        // Note: Adjust this based on your actual bread deliveries API
        // await breadDeliveriesApi.create({
        //   year,
        //   delivery_week: deliveryWeek,
        //   delivery_day: deliveryDay,
        //   subscription: subscription.id,
        //   bread: breadId,
        // });
      } catch (error) {
        console.error('Failed to add bread:', error);
        setSelectedBreads(selectedBreads); // Revert
      } finally {
        setSaving(false);
      }
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
      {/* Summary */}
      <div className="alert alert-info mb-3">
        <strong>{selectedBreads.length} / {maxBreads}</strong> Brote ausgewählt
        {remainingSlots > 0 && ` (noch ${remainingSlots} verfügbar)`}
      </div>

      {/* Bread Cards */}
      <div className="d-flex flex-wrap gap-3">
        {breads.map(bread => {
          const qty = getQuantityForBread(bread.id);
          const contents = contentsMap[bread.id] || [];

          return (
            <div key={bread.id} style={{ width: '280px', flex: '0 0 280px' }}>
              <div 
                className="card h-100 shadow-sm"
                style={{ 
                  border: qty > 0 ? '2px solid #8B4513' : '1px solid #dee2e6',
                  opacity: remainingSlots === 0 && qty === 0 ? 0.6 : 1,
                }}
              >
                {/* Image */}
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
                    <span className="material-icons" style={{ fontSize: '48px', color: '#D4A574' }}>
                      bakery_dining
                    </span>
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
                        {contents.map(c => c.ingredient_name).join(', ')}
                      </small>
                    </div>
                  )}

                  {bread.price && (
                    <p className="mb-2 fw-bold" style={{ color: '#8B4513' }}>
                      {Number(bread.price).toFixed(2)} €
                    </p>
                  )}

                  {/* Quantity controls */}
                  <div className="d-flex align-items-center justify-content-center gap-2 mt-auto">
                    <button
                      className="btn btn-sm rounded-circle"
                      style={{ 
                        width: '32px', 
                        height: '32px',
                        backgroundColor: qty > 0 ? '#D4A574' : '#e9ecef',
                        color: qty > 0 ? 'white' : '#6c757d',
                      }}
                      onClick={() => handleToggleBread(bread.id)}
                      disabled={qty === 0 || saving}
                    >
                      <span className="material-icons" style={{ fontSize: '18px' }}>remove</span>
                    </button>

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
                      onClick={() => handleToggleBread(bread.id)}
                      disabled={remainingSlots === 0 || saving}
                    >
                      <span className="material-icons" style={{ fontSize: '18px' }}>add</span>
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