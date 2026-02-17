import React from 'react';
import { createRoot } from 'react-dom/client';
import { Reports } from '../pages/Reports.tsx';

const container = document.getElementById('reports-root');

if (container) {
  const root = createRoot(container);
  root.render(<Reports />);
}