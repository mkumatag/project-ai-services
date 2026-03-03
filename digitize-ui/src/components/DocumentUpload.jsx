import { useState } from 'react';
import {
  FileUploader,
  Button,
  RadioButtonGroup,
  RadioButton,
  InlineNotification,
  Loading,
} from '@carbon/react';
import { Upload } from '@carbon/icons-react';
import { uploadDocuments } from '../services/api';

const DocumentUpload = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState([]);
  const [operation, setOperation] = useState('ingestion');
  const [outputFormat, setOutputFormat] = useState('json');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    setFiles(selectedFiles);
    setError(null);
    setSuccess(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload');
      return;
    }

    if (operation === 'digitization' && files.length > 1) {
      setError('Only 1 file allowed for digitization operation');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await uploadDocuments(files, operation, outputFormat);
      setSuccess(`Upload successful! Job ID: ${result.job_id}`);
      setFiles([]);
      
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="document-upload">
      <h3>Upload Documents</h3>
      
      <div style={{ marginBottom: '1rem' }}>
        <RadioButtonGroup
          legendText="Operation Type"
          name="operation"
          valueSelected={operation}
          onChange={(value) => setOperation(value)}
        >
          <RadioButton
            labelText="Ingestion (Process and store in vector DB)"
            value="ingestion"
            id="operation-ingestion"
          />
          <RadioButton
            labelText="Digitization (Convert document only)"
            value="digitization"
            id="operation-digitization"
          />
        </RadioButtonGroup>
      </div>

      {operation === 'digitization' && (
        <div style={{ marginBottom: '1rem' }}>
          <RadioButtonGroup
            legendText="Output Format"
            name="outputFormat"
            valueSelected={outputFormat}
            onChange={(value) => setOutputFormat(value)}
          >
            <RadioButton labelText="JSON" value="json" id="format-json" />
            <RadioButton labelText="Markdown" value="md" id="format-md" />
            <RadioButton labelText="Text" value="text" id="format-text" />
          </RadioButtonGroup>
        </div>
      )}

      <FileUploader
        labelTitle="Upload files"
        labelDescription="Max file size is 500mb. Supported file types: PDF"
        buttonLabel="Select files"
        filenameStatus="edit"
        accept={['.pdf']}
        multiple={operation === 'ingestion'}
        onChange={handleFileChange}
        size="md"
      />

      {files.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <p>Selected files: {files.map(f => f.name).join(', ')}</p>
        </div>
      )}

      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
          style={{ marginTop: '1rem', maxWidth: '100%' }}
        />
      )}

      {success && (
        <InlineNotification
          kind="success"
          title="Success"
          subtitle={success}
          onCloseButtonClick={() => setSuccess(null)}
          style={{ marginTop: '1rem', maxWidth: '100%' }}
        />
      )}

      <Button
        renderIcon={Upload}
        onClick={handleUpload}
        disabled={loading || files.length === 0}
        style={{ marginTop: '1rem' }}
      >
        {loading ? 'Uploading...' : 'Upload'}
      </Button>

      {loading && <Loading description="Uploading documents..." withOverlay={false} />}
    </div>
  );
};

export default DocumentUpload;

// Made with Bob
