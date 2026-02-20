import React from 'react';
import { createRoot } from 'react-dom/client';
import { WeeklyPlanBreads } from '../pages/WeeklyPlanBreads.tsx';

const container = document.getElementById('weekly-plan-breads-root');

if (container) {
  const csrfToken = container.getAttribute('data-csrf-token') || '';
  const root = createRoot(container);
  root.render(<WeeklyPlanBreads csrfToken={csrfToken} />);
}

