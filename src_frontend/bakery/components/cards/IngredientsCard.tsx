import React, { useState, useEffect } from 'react';
import { IngredientModal } from '../modals/IngredientModal';
import { Pencil, Trash } from 'react-bootstrap-icons';
import { BakeryApi, Configuration } from '../../../api-client';
import TapirButton from '../../../components/TapirButton';
import { useApi } from '../../../hooks/useApi';
import { handleRequestError } from '../../../utils/handleRequestError';
import type { Ingredient, IngredientRequest } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface IngredientsCardProps {
  csrfToken: string;
}

export const IngredientsCard: React.FC<IngredientsCardProps> = ({ csrfToken }) => {
  
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingIngredient, setEditingIngredient] = useState<Ingredient | null>(null);
  const [showOnlyActive, setShowOnlyActive] = useState(true);


  useEffect(() => {
    loadIngredients();
  }, []);

  const loadIngredients = () => {
    setLoading(true);
    bakeryApi.bakeryIngredientsList({})
      .then((data) => {
        setIngredients(data);
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Laden der Zutaten');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const filteredIngredients = ingredients.filter(ingredient => {
    return showOnlyActive ? ingredient.isActive !== false : true;
  });

  const handleCreate = () => {
    setEditingIngredient(null);
    setShowModal(true);
  };

  const handleEdit = (ingredient: Ingredient) => {
    setEditingIngredient(ingredient);
    setShowModal(true);
  };

  const handleSave = (ingredient: IngredientRequest) => {
    const promise = editingIngredient
      ? bakeryApi.bakeryIngredientsPartialUpdate({
          id: editingIngredient.id!,
          patchedIngredientRequest: ingredient
        })
      : bakeryApi.bakeryIngredientsCreate({
          ingredientRequest: ingredient
        });

    promise
      .then(() => {
        loadIngredients();
        setShowModal(false);
        setEditingIngredient(null);
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Speichern der Zutat');
      });
  };

  const handleDelete = (id: string) => {
    if (!confirm('Zutat wirklich löschen?')) return;

    bakeryApi.bakeryIngredientsDestroy({ id })
      .then(() => {
        loadIngredients();
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Löschen der Zutat');
      });
  };

  return (
    <>
      <div className="card h-100 shadow-sm">
        <div className="card-header border-0 d-flex justify-content-between align-items-center header-bakery-ingredients">
          <h5 className="mb-0">Zutaten</h5>
          <div className="d-flex align-items-center gap-3">
            <div className="form-check form-check-sm mb-0">
              <input
                className="form-check-input checkbox-ingredients"
                type="checkbox"
                id="showOnlyActiveIngredients"
                checked={showOnlyActive}
                onChange={(e) => setShowOnlyActive(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="showOnlyActiveIngredients" style={{ fontSize: '0.875rem', whiteSpace: 'nowrap' }}>
                nur aktive
              </label>
            </div>
            <TapirButton
              variant=""
              className="btn-bakery-ingredients"
              size="sm"
              icon="add"
              text="neu"
              onClick={handleCreate}
              style={{ paddingTop: 0, paddingBottom: 0 }}
            />
          </div>
        </div>
        
        <div className="card-body card-body-ingredients">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border spinner-ingredients" role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : filteredIngredients.length === 0 ? (
            <div className="text-center py-4 text-muted">
              {showOnlyActive ? (
                <>
                  <p>Keine aktiven Zutaten vorhanden.</p>
                  <TapirButton variant="outline-secondary" size="sm" text="Alle anzeigen" onClick={() => setShowOnlyActive(false)} />
                </>
              ) : (
                <>
                  <p>Noch keine Zutaten vorhanden.</p>
                  <TapirButton variant="outline-secondary" size="sm" text="Erste Zutat hinzufügen" onClick={handleCreate} />
                </>
              )}
            </div>
          ) : (
            <div className="list-group list-group-flush">
              {filteredIngredients.map((ingredient) => (
                <div key={ingredient.id} className="list-group-item px-0 d-flex justify-content-between align-items-start border-0 list-item-transparent">
                  <div className="flex-grow-1">
                    <h6 className="mb-1">
                      {ingredient.name}
                      {ingredient.isOrganic && (
                        <span className="badge ms-2 badge-bio">Bio</span>
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
                      className="btn btn-outline-secondary border-0 icon-bakery-muted" 
                      title="Bearbeiten"
                      onClick={() => handleEdit(ingredient)}
                    >
                      <Pencil size={16} />
                    </button>
                    {ingredient.canBeDeleted !== false && (
                      <button 
                        className="btn btn-outline-danger border-0" 
                        title="Löschen"
                        onClick={() => handleDelete(ingredient.id!)}
                      >
                        <Trash size={16} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
                        
        <div className="card-footer border-0 text-muted card-footer-ingredients">
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