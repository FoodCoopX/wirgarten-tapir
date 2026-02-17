import React, { useState, useEffect } from 'react';
import { IngredientModal } from '../modals/IngredientModal';
import { BakeryApi, Configuration } from '../../../api-client';
import type { Ingredient, IngredientRequest } from '../../../api-client/models';

// Create API instance
const config = new Configuration({
  basePath: '',
});
const bakeryApi = new BakeryApi(config);

export const IngredientsCard: React.FC = () => {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingIngredient, setEditingIngredient] = useState<Ingredient | null>(null);
  const [showOnlyActive, setShowOnlyActive] = useState(true);

  useEffect(() => {
    loadIngredients();
  }, [showOnlyActive]);

  const loadIngredients = async () => {
    setLoading(true);
    try {
      const data = await bakeryApi.bakeryIngredientsList({
        isActive: showOnlyActive ? true : undefined
      });
      setIngredients(data);
    } catch (error) {
      console.error('Failed to load ingredients:', error);
      alert('Fehler beim Laden der Zutaten');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingIngredient(null);
    setShowModal(true);
  };

  const handleEdit = (ingredient: Ingredient) => {
    setEditingIngredient(ingredient);
    setShowModal(true);
  };

  const handleSave = async (ingredient: IngredientRequest) => {
    try {
      if (editingIngredient) {
        await bakeryApi.bakeryIngredientsPartialUpdate({
          id: editingIngredient.id,
          patchedIngredientRequest: ingredient
        });
      } else {
        await bakeryApi.bakeryIngredientsCreate({
          ingredientRequest: ingredient
        });
      }

      await loadIngredients();
      setShowModal(false);
      setEditingIngredient(null);
    } catch (error) {
      console.error('Failed to save ingredient:', error);
      alert('Fehler beim Speichern der Zutat');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Zutat wirklich löschen?')) return;

    try {
      await bakeryApi.bakeryIngredientsDestroy({ id });
      await loadIngredients();
    } catch (error) {
      console.error('Failed to delete ingredient:', error);
      alert('Fehler beim Löschen der Zutat');
    }
  };

  return (
    <>
      <div className="card h-100 shadow-sm">
        <div className="card-header border-0 d-flex justify-content-between align-items-center" 
             style={{ backgroundColor: '#F0F4E8', color: '#5D7A4A' }}>
          <h5 className="mb-0">Zutaten</h5>
          <div className="d-flex align-items-center gap-3">
            <div className="form-check form-check-sm mb-0">
              <input
                className="form-check-input"
                type="checkbox"
                id="showOnlyActiveIngredients"
                checked={showOnlyActive}
                onChange={(e) => setShowOnlyActive(e.target.checked)}
                style={{
                  backgroundColor: showOnlyActive ? '#5D7A4A' : 'transparent',
                  borderColor: '#5D7A4A'
                }}
              />
              <label className="form-check-label" htmlFor="showOnlyActiveIngredients" style={{ fontSize: '0.875rem', whiteSpace: 'nowrap' }}>
                nur aktive
              </label>
            </div>
            <button 
              className="btn btn-sm py-0" 
              style={{ backgroundColor: '#5D7A4A', color: 'white' }}
              onClick={handleCreate}
            >
              <span className="material-icons" style={{ fontSize: '16px', color: 'white' }}>+ </span>
              neu
            </button>
          </div>
        </div>
        
        <div className="card-body" style={{ backgroundColor: '#F9FBF7' }}>
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" style={{ color: '#5D7A4A' }} role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : ingredients.length === 0 ? (
            <div className="text-center py-4 text-muted">
              {showOnlyActive ? (
                <>
                  <p>Keine aktiven Zutaten vorhanden.</p>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowOnlyActive(false)}>
                    Alle anzeigen
                  </button>
                </>
              ) : (
                <>
                  <p>Noch keine Zutaten vorhanden.</p>
                  <button className="btn btn-sm btn-outline-secondary" onClick={handleCreate}>
                    Erste Zutat hinzufügen
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="list-group list-group-flush">
              {ingredients.map((ingredient) => (
                <div key={ingredient.id} className="list-group-item px-0 d-flex justify-content-between align-items-start border-0"
                     style={{ backgroundColor: 'transparent' }}>
                  <div className="flex-grow-1">
                    <h6 className="mb-1">
                      {ingredient.name}
                      {ingredient.isOrganic && (
                        <span className="badge ms-2" style={{ backgroundColor: '#81C784', color: 'white' }}>Bio</span>
                      )}
                      {!ingredient.isActive && (
                        <span className="badge bg-secondary ms-2">inaktiv</span>
                      )}
                    </h6>
                    {ingredient.description && (
                      <small className="text-muted">{ingredient.description}</small>
                    )}
                  </div>
                  <div className="btn-group btn-group-sm ms-2">
                    <button 
                      className="btn btn-outline-secondary border-0" 
                      title="Bearbeiten"
                      style={{ color: '#757575' }}
                      onClick={() => handleEdit(ingredient)}
                    >
                      <span className="material-icons" style={{ fontSize: '16px' }}>edit</span>
                    </button>
                    {ingredient.canBeDeleted !== false && (
                      <button 
                        className="btn btn-outline-danger border-0" 
                        title="Löschen"
                        onClick={() => handleDelete(ingredient.id)}
                      >
                        <span className="material-icons" style={{ fontSize: '16px' }}>delete</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="card-footer border-0 text-muted" style={{ backgroundColor: '#F9FBF7' }}>
          <small>
            {ingredients.length} Zutat{ingredients.length !== 1 ? 'en' : ''}
          </small>
        </div>
      </div>

      {showModal && (
        <IngredientModal
          ingredient={editingIngredient}
          onSave={handleSave}
          onClose={() => {
            setShowModal(false);
            setEditingIngredient(null);
          }}
        />
      )}
    </>
  );
};