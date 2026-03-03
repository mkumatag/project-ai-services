import { useState } from 'react';
import { Tabs, TabList, Tab, TabPanels, TabPanel } from '@carbon/react';
import DocumentUpload from '../components/DocumentUpload';
import JobMonitor from '../components/JobMonitor';
import DocumentList from '../components/DocumentList';

const HomePage = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = (result) => {
    console.log('Upload successful:', result);
    // Trigger refresh of job monitor and document list
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="home-page">
      <Tabs>
        <TabList aria-label="Document processing tabs">
          <Tab>Upload Documents</Tab>
          <Tab>Job Monitor</Tab>
          <Tab>Documents</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          </TabPanel>
          <TabPanel>
            <JobMonitor refreshTrigger={refreshTrigger} />
          </TabPanel>
          <TabPanel>
            <DocumentList refreshTrigger={refreshTrigger} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  );
};

export default HomePage;

// Made with Bob
