import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import DocumentUploadPage from './pages/DocumentUploadPage';
import JobMonitorPage from './pages/JobMonitorPage';
import DocumentListPage from './pages/DocumentListPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/upload" replace />} />
        
        <Route element={<MainLayout />}>
          <Route path="/upload" element={<DocumentUploadPage />} />
          <Route path="/jobs" element={<JobMonitorPage />} />
          <Route path="/documents" element={<DocumentListPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

// Made with Bob
