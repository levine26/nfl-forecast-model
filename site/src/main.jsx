import React from 'react'
import ReactDOM from 'react-dom/client'
import AppCoherent from './AppCoherent.jsx'
import AppVNextPrototype from './vnext/AppVNextPrototype.jsx'

const base=String(import.meta.env.BASE_URL||'/').replace(/\/+$/,'')
const pathname=window.location.pathname
const appPath=base && pathname.startsWith(base) ? (pathname.slice(base.length)||'/') : pathname
const vNextRoute=/^\/(?:week\/\d+|game\/[^/]+|team\/[^/]+|history|methodology)\/?$/.test(appPath)
const App=vNextRoute ? AppVNextPrototype : AppCoherent

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
