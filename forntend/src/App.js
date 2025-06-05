import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import PredefinedKnowledge from './pages/PredefinedKnowledge';
import LearnedKnowledge from './pages/LearnedKnowledge';
import HelpRequests from './pages/HelpRequests';
import LiveKitRoom from './pages/LiveKitRoom';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/knowledge-base/predefined" element={<PredefinedKnowledge />} />
          <Route path="/knowledge-base/learned" element={<LearnedKnowledge />} />
          <Route path="/help-requests" element={<HelpRequests />} />
          <Route path="/livekit" element={<LiveKitRoom />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App; 