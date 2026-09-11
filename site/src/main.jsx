import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './AppCoherent.jsx'
import './levline-3-launch.css'

document.title = 'Sunday Signal — Powered by LevLine 3.0'
document.documentElement.dataset.levlineVersion = '3.0'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
