import React from 'react';
import { createRoot } from 'react-dom/client';
import { IngredientsLabelsBreads } from '../pages/IngredientsLabelsBreads.tsx';

const container = document.getElementById('ingredients-labels-breads-root');

if (container) {
  const root = createRoot(container);
  root.render(<IngredientsLabelsBreads />);
}