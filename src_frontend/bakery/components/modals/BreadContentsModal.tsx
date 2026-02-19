import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { Plus, Trash } from 'react-bootstrap-icons';
import { BakeryApi } from '../../../api-client';
import { useApi } from '../../../hooks/useApi';
import type { Ingredient, BreadContent, BreadContentRequest, BreadList } from '../../../api-client/models';

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

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);


  const loadData = async () => {
    setLoading(true);
    try {
      const [contentsData, ingredientsData] = await Promise.all([
        bakeryApi.bakeryBreadcontentsList({ bread: bread.id! }),
        bakeryApi.bakeryIngredientsList()
      ]);
      setContents(contentsData);
      setAvailableIngredients(ingredientsData);
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!selectedIngredient) return;

    const payload: BreadContentRequest = {
      bread: bread.id!,
      ingredient: selectedIngredient,
      amount: amount,
      sortOrder: contents.length,
    };

    try {
      await bakeryApi.bakeryBreadcontentsCreate({
        breadContentRequest: payload
      });
      await loadData();
      setSelectedIngredient('');
      setAmount('100');
    } catch (error) {
      console.error('Failed to add ingredient:', error);
      alert('Fehler beim Hinzufügen der Zutat');
    }
  };

  const handleDelete = async (contentId: string) => {
    
    try {
      await bakeryApi.bakeryBreadcontentsDestroy({
        id: contentId
      });
      setContents(prev => prev.filter(c => c.id !== contentId));
    } catch (error) {
      console.error('Failed to delete content:', error);
      alert('Fehler beim Löschen der Zutat');
    }
  };


  const modalContent = (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          zIndex: 9999,
        }}
        onClick={onClose}
      />

      {/* Modal Content */}
      <div
        style={{
          position: 'relative',
          zIndex: 10000,
          width: '100%',
          maxWidth: '800px',
          maxHeight: '85vh',
          overflow: 'auto',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}
      >
        <div 
          className="p-3 d-flex justify-content-between align-items-center" 
          style={{ backgroundColor: '#F5E6D3', color: '#8B4513', borderRadius: '8px 8px 0 0' }}
        >
          <h5 className="mb-0">
            Inhaltsstoffe: {bread.name}
          </h5>
          <button type="button" className="btn-close" onClick={onClose}></button>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" style={{ color: '#8B4513' }} role="status">
                <span className="visually-hidden">Lädt...</span>
              </div>
            </div>
          ) : (
            <>
              {/* Add New Ingredient */}
              <div className="card mb-4 border-0" style={{ backgroundColor: '#FBF8F3' }}>
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
                      <button
                        type="button"
                        className="btn w-100 d-inline-flex align-items-center justify-content-center"
                        style={{ backgroundColor: '#8B4513', color: 'white' }}
                        onClick={handleAdd}
                        disabled={!selectedIngredient}
                      >
                        <Plus size={16} />
                      </button>
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
        </div>

        <div className="p-3 border-top d-flex justify-content-end" style={{ borderRadius: '0 0 8px 8px' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Schließen
          </button>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};