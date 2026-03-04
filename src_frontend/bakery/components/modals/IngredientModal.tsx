import React, { useState, useEffect } from 'react';
import type { Ingredient, IngredientRequest } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface IngredientModalProps {
  ingredient: Ingredient | null;
  onSave: (ingredient: IngredientRequest) => void;
  onClose: () => void;
}

export const IngredientModal: React.FC<IngredientModalProps> = ({
  ingredient,
  onSave,
  onClose,
}) => {
  const [formData, setFormData] = useState<IngredientRequest>({
    name: '',
    description: '',
    isOrganic: false,
    isActive: true,
  });

  useEffect(() => {
    if (ingredient) {
      setFormData({
        name: ingredient.name,
        description: ingredient.description || '',
        isOrganic: ingredient.isOrganic,
        isActive: ingredient.isActive,
      });
    }
  }, [ingredient]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header" style={{ backgroundColor: '#F0F4E8', color: '#5D7A4A' }}>
            <h5 className="modal-title">
              {ingredient ? 'Zutat bearbeiten' : 'Neue Zutat'}
            </h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label htmlFor="name" className="form-label fw-bold">
                  Name <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="z.B. Weizenmehl"
                />
              </div>

              <div className="mb-3">
                <label htmlFor="description" className="form-label fw-bold">
                  Beschreibung
                </label>
                <textarea
                  className="form-control"
                  id="description"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="z.B. Type 550"
                />
              </div>

              
              <div className="form-check form-switch mb-3">
                <input
                  className="form-check-input form-switch-bakery"
                  type="checkbox"
                  id="is_organic"
                  checked={formData.isOrganic}
                  onChange={(e) => setFormData({ ...formData, isOrganic: e.target.checked })}
                />
                <label className="form-check-label" htmlFor="is_organic">
                  <span className="badge badge-bio">Bio</span>
                  {' '}
                </label>
              </div>
               <div className="form-check form-switch">
                <input
                  className="form-check-input form-switch-bakery"
                  type="checkbox"
                  id="isActive"
                  checked={formData.isActive}
                  onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                />
                <label className="form-check-label" htmlFor="isActive">
                  aktiv
                </label>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Abbrechen
              </button>
              <button type="submit" className="btn" style={{ backgroundColor: '#5D7A4A', color: 'white' }}>
                Speichern & Schließen
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};