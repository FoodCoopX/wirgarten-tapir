import React, { useState, useEffect } from 'react';
import { Modal } from 'react-bootstrap';
import { Trash } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import TapirButton from '../../../components/TapirButton';
import { useApi } from '../../../hooks/useApi';
import { handleRequestError } from '../../../utils/handleRequestError';
import type { Ingredient, BreadContent, BreadContentRequest, BreadList } from '../../../api-client/models';
import '../../styles/bakery_styles.css';

interface BreadContentsModalProps {
  bread: BreadList;
  csrfToken: string;
  onClose: () => void;
}

export const BreadContentsModal: React.FC<BreadContentsModalProps> = ({ bread, csrfToken, onClose }) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [contents, setContents] = useState<BreadContent[]>([]);
  const [availableIngredients, setAvailableIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIngredient, setSelectedIngredient] = useState('');
  const [amount, setAmount] = useState('100');

  useEffect(() => {
    loadData();
  }, [bread.id]);



  const loadData = () => {
    setLoading(true);
    Promise.all([
      bakeryApi.bakeryBreadcontentsList({ bread: bread.id! }),
      bakeryApi.bakeryIngredientsList()
    ])
      .then(([contentsData, ingredientsData]) => {
        setContents(contentsData);
        setAvailableIngredients(ingredientsData);
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Laden der Daten');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleAdd = () => {
    if (!selectedIngredient) return;

    const payload: BreadContentRequest = {
      bread: bread.id!,
      ingredient: selectedIngredient,
      amount: Number(amount),
      sortOrder: contents.length,
    };

    bakeryApi.bakeryBreadcontentsCreate({
      breadContentRequest: payload
    })
      .then(() => {
        loadData();
        setSelectedIngredient('');
        setAmount('100');
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Hinzufügen der Zutat');
      });
  };

  const handleDelete = (contentId: string) => {
    
    bakeryApi.bakeryBreadcontentsDestroy({
      id: contentId
    })
      .then(() => {
        setContents(prev => prev.filter(c => c.id !== contentId));
      })
      .catch((error) => {
        handleRequestError(error, 'Fehler beim Löschen der Zutat');
      });
  };


  return (
    <Modal show onHide={onClose} size="lg" centered>
      <Modal.Header closeButton className="header-darkbrown-on-sahara">
        <Modal.Title>Inhaltsstoffe: {bread.name}</Modal.Title>
      </Modal.Header>

      <Modal.Body>
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-bakery-primary-dark" role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : (
            <>
              {/* Add New Ingredient */}
              <div className="card mb-4 border-0 card-body-bakery">
                <div className="card-body">
                  <h6 className="card-title mb-3">Zutat hinzufügen</h6>
                  <div className="row g-2 align-items-end">
                    <div className="col-md-6">
                      <label className="form-label">Zutat</label>
                      <select
                        className="form-select"
                        value={selectedIngredient}
                        onChange={(e) => setSelectedIngredient(e.target.value)}
                      >
                        <option value="">-- Zutat wählen --</option>
                        {availableIngredients
                          .filter(ing => !contents.some(c => c.ingredient === ing.id))
                          .map(ingredient => (
                            <option key={ingredient.id} value={ingredient.id}>
                              {ingredient.name}
                            </option>
                          ))}
                      </select>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Menge (g)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        min="0"
                        step="1"
                      />
                    </div>
                    <div className="col-md-2">
                      <TapirButton
                        variant=""
                        className="dark-brown-button w-100"
                        icon="add"
                        onClick={handleAdd}
                        disabled={!selectedIngredient}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Existing Ingredients List */}
              {contents.length === 0 ? (
                <div className="text-center text-muted py-4">
                  Noch keine Zutaten hinzugefügt.
                </div>
              ) : (
                <div className="list-group">
                  {contents.map((content) => (
                    <div key={content.id} className="list-group-item d-flex justify-content-between align-items-center">
                      <div className="flex-grow-1">
                        <strong>{content.ingredientName}</strong>
                      </div>
                      <div className="d-flex align-items-center gap-2">
                        <strong>{content.amount}</strong>
                        <span className="text-muted">g</span>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => handleDelete(content.id!)}
                        >
                          <Trash size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {contents.length > 0 && (
                <div className="mt-3 text-end">
                  <strong>Summe: {contents.reduce((sum, c) => sum + Number(c.amount), 0)}g</strong>
                </div>
              )}
            </>
          )}
      </Modal.Body>

      <Modal.Footer>
        <TapirButton variant="" className="dark-brown-button" text="Speichern & Schließen" icon="save" onClick={onClose} />
      </Modal.Footer>
    </Modal>
  );
};