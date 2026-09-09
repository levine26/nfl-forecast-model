import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './AppPublicationVNext.jsx'
import './calibration-polish.css'
import { installCalibrationPresentationAdapter } from './calibration-presentation.js'

installCalibrationPresentationAdapter()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
