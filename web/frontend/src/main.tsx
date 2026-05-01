import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

window.addEventListener('vite:preloadError', () => {
  const reloadKey = 'translation-agent:preload-reload';
  if (sessionStorage.getItem(reloadKey) === '1') {
    return;
  }
  sessionStorage.setItem(reloadKey, '1');
  window.location.reload();
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
