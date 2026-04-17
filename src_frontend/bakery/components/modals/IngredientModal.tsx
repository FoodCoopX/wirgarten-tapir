import React, { useState, useEffect } from 'react';
import type { Ingredient, IngredientRequest } from '../../../api-client/models';
import TapirButton from '../../../components/TapirButton';
import { Modal } from 'react-bootstrap';
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
    <Modal show onHide={onClose} centered>
      <Modal.Header closeButton className="header-bakery-ingredients">
        <Modal.Title>{ingredient ? 'Zutat bearbeiten' : 'Neue Zutat'}</Modal.Title>
      </Modal.Header>
          
      <form onSubmit={handleSubmit}>
        <Modal.Body>
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
        </Modal.Body>
            
        <Modal.Footer>
          <TapirButton variant="secondary" text="Abbrechen" onClick={onClose} />
          <TapirButton variant="" className="btn-bakery-ingredients" text="Speichern & Schließen" icon="save" type="submit" />
        </Modal.Footer>
      </form>
    </Modal>
  );
};