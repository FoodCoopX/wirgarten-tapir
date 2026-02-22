import { createRoot } from 'react-dom/client';
import { ChooseBreads } from '../pages/ChooseBreads';

const container = document.getElementById('choose-breads-root');

if (container) {
  const memberId = container.dataset.memberId || '';
  const csrfToken = container.dataset.csrfToken || '';
  const chooseStationPerBread = container.dataset.chooseStationPerBread === 'True'; // Add this line

  const root = createRoot(container);
  root.render(<ChooseBreads chooseStationPerBread={chooseStationPerBread} memberId={memberId} csrfToken={csrfToken} />);
}