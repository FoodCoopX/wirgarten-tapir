import React from 'react';
import { createRoot } from 'react-dom/client';
import { IngredientsLabelsBreads } from '../pages';

const container = document.getElementById('ingredients-labels-breads-root');

if (container) {
  const csrfToken = container.getAttribute('data-csrf-token') || '';
  const root = createRoot(container);
  root.render(<IngredientsLabelsBreads csrfToken={csrfToken} />);
}