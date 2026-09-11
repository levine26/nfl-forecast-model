import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './AppPublicationVNext.jsx'
import './calibration-polish.css'
import { installCalibrationPresentationAdapter } from './calibration-presentation.js'
import { installFstProductionPresentationAdapter } from './fst-production-presentation.js'

installCalibrationPresentationAdapter()
installFstProductionPresentationAdapter()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
