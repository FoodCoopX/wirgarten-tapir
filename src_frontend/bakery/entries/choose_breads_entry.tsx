import { createRoot } from 'react-dom/client';
import { ChooseBreads } from '../pages/ChooseBreads';

const container = document.getElementById('choose-breads-root');

if (container) {
  const memberId = container.dataset.memberId || '';
  const csrfToken = container.dataset.csrfToken || '';
  const chooseStationPerBread = container.dataset.chooseStationPerBread === 'True'; 
  const membersCanChooseBreadSorts = container.dataset.membersCanChooseBreadSorts === 'True';

  const root = createRoot(container);
  root.render(<ChooseBreads chooseStationPerBread={chooseStationPerBread} membersCanChooseBreadSorts={membersCanChooseBreadSorts} memberId={memberId} csrfToken={csrfToken} />);
}