import { createRoot } from 'react-dom/client';
import { ChooseBreads } from '../pages/ChooseBreads';

const container = document.getElementById('choose-breads-root');

if (container) {
  const memberId = container.dataset.memberId || '';
  const root = createRoot(container);
  root.render(<ChooseBreads memberId={memberId} />);
}