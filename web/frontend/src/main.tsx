import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// 字体自托管：宋体按 unicode-range 切成约百个分片，页面只下载实际用到的字
import '@fontsource/noto-serif-sc/400.css' // 工作台中文正文用宋体
import '@fontsource-variable/source-serif-4/wght.css' // 工作台英文原文
import '@fontsource/noto-serif-sc/600.css'
import '@fontsource-variable/inter/wght.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
