import React from 'react'
import ReactDOM from 'react-dom/client'
import AppCoherent from './AppCoherent.jsx'

const AppVNextPrototype=React.lazy(()=>import('./vnext/AppVNextPrototype.jsx'))
const base=String(import.meta.env.BASE_URL||'/').replace(/\/+$/,'')
const pathname=window.location.pathname
const appPath=base && pathname.startsWith(base) ? (pathname.slice(base.length)||'/') : pathname
const vNextRoute=/^\/(?:week\/\d+|game\/[^/]+|team\/[^/]+|history|methodology)\/?$/.test(appPath)

const surface=vNextRoute
  ? <React.Suspense fallback={<div role="status" style={{padding:'2rem'}}>Loading Sunday Signal…</div>}><AppVNextPrototype/></React.Suspense>
  : <AppCoherent/>

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {surface}
  </React.StrictMode>,
)
