import React, { useState, useEffect } from 'react';
import { labelsApi, profileApi } from '../../types/client';
import type { BreadLabel } from '../../types/api';

interface PreferredLabelsCardProps {
  memberId: string;
}

export const PreferredLabelsCard: React.FC<PreferredLabelsCardProps> = ({ memberId }) => {
  const [labels, setLabels] = useState<BreadLabel[]>([]);
  const [selectedLabelIds, setSelectedLabelIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadLabels = async () => {
      try {
        const allLabels = await labelsApi.list();
        setLabels(allLabels.filter(l => l.is_active));
        
        // Load user's preferred labels
        const profile = await profileApi.getProfile(memberId);
        if (profile.preferred_bread_labels) {
          setSelectedLabelIds(new Set(profile.preferred_bread_labels));
        }
        
        setLoading(false);
      } catch (error) {
        console.error('Failed to load labels:', error);
        setLoading(false);
      }
    };
    loadLabels();
  }, [memberId]);

  const toggleLabel = async (labelId: string) => {
    const newSelected = new Set(selectedLabelIds);
    
    if (newSelected.has(labelId)) {
      newSelected.delete(labelId);
    } else {
      newSelected.add(labelId);
    }
    
    setSelectedLabelIds(newSelected);
    
    // Save to backend
    try {
      await profileApi.updatePreferredLabels(Array.from(newSelected), memberId);
    } catch (error) {
      console.error('Failed to save preferred labels:', error);
      // Revert on error
      setSelectedLabelIds(selectedLabelIds);
    }
  };

  return (
    <div className="card">
      <div 
        className="card-header d-flex justify-content-between align-items-center"
        style={{ backgroundColor: '#F5E6D3', borderBottom: '1px solid #D4A574', color: '#8B4513' }}
      >
        <h5 className="mb-0" style={{ color: '#8B4513' }}>Bevorzugte Brotlabels</h5>
        <small style={{ color: '#8B4513', opacity: 0.75 }}>
          {selectedLabelIds.size} ausgewählt
        </small>
      </div>

      <div className="card-body">
        {loading ? (
          <div className="text-center py-3">
            <div className="spinner-border spinner-border-sm">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : labels.length === 0 ? (
          <p className="text-muted mb-0">Keine Labels verfügbar.</p>
        ) : (
          <>
            <p className="text-muted small mb-3">
              Wähle deine bevorzugten Brotarten aus. 
              Es werden dir dann nur Brote angezeigt, die diese Labels tragen.
            </p>
            <div className="d-flex flex-wrap gap-2">
              {labels.map((label) => {
                const isSelected = selectedLabelIds.has(label.id);
                return (
                  <button
                    key={label.id}
                    type="button"
                    className={`btn btn-sm ${isSelected ? 'btn-success' : 'btn-outline-secondary'}`}
                    onClick={() => toggleLabel(label.id)}
                    style={{
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      padding: '0.2rem 0.6rem',
                      fontSize: '0.85rem',
                    }}
                  >
                    {isSelected && <span className="me-1">✓</span>}
                    {label.name}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>
      <div className="card-footer text-muted">
        <small>
          <span className="material-icons" style={{ fontSize: '14px', verticalAlign: 'middle' }}>info</span>
          {' '}Änderungen werden automatisch gespeichert
        </small>
      </div>
    </div>
  );
};