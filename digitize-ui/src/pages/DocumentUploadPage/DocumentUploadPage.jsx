import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@carbon/ibm-products';
import {
  Grid,
  Column,
  FileUploader,
  Button,
  RadioButtonGroup,
  RadioButton,
  InlineNotification,
  Loading,
  Tile,
  ProgressIndicator,
  ProgressStep,
  Accordion,
  AccordionItem,
} from '@carbon/react';
import { Upload, DocumentPdf, Close, Checkmark, Renew, View } from '@carbon/icons-react';
import { uploadDocuments } from '../../services/api';
import styles from './DocumentUploadPage.module.scss';

const DocumentUploadPage = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [operation, setOperation] = useState('ingestion');
  const [outputFormat, setOutputFormat] = useState('json');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [fileUploaderKey, setFileUploaderKey] = useState(0);
  const [isFileListExpanded, setIsFileListExpanded] = useState(true);
  const [isCompleted, setIsCompleted] = useState(false);
  const [jobId, setJobId] = useState(null);

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    setFiles(selectedFiles);
    setError(null);
    setSuccess(null);
    if (selectedFiles.length > 0) {
      setCurrentStep(2);
    }
  };

  const handleOperationChange = (value) => {
    setOperation(value);
    setCurrentStep(1);
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
      setJobId(result.job_id);
      setSuccess(`Upload successful! Job ID: ${result.job_id}`);
      setFiles([]);
      setCurrentStep(3);
      setIsCompleted(true);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadMore = () => {
    setIsCompleted(false);
    setSuccess(null);
    setJobId(null);
    setCurrentStep(0);
    setOperation('ingestion');
    setOutputFormat('json');
    setFiles([]);
    setFileUploaderKey(prev => prev + 1);
  };

  const handleViewJobs = () => {
    navigate('/jobs');
  };

  return (
    <>
      <PageHeader
        title={{ text: 'Upload Documents' }}
        subtitle="Upload PDF documents for processing and digitization"
      />

      <Grid fullWidth className={styles.mainGrid}>
        {/* Left Column - Form */}
        <Column lg={10} md={6} sm={4}>
          <div className={styles.uploadContent}>
            {/* Progress Indicator */}
            <div className={styles.progressSection}>
              <ProgressIndicator currentIndex={currentStep} spaceEqually>
                <ProgressStep
                  label="Select operation"
                  description="Choose processing type"
                />
                <ProgressStep
                  label="Upload files"
                  description="Select PDF documents"
                />
                <ProgressStep
                  label="Process"
                  description="Submit for processing"
                />
                <ProgressStep
                  label="Complete"
                  description="View results"
                />
              </ProgressIndicator>
            </div>

            {/* Completion State */}
            {isCompleted ? (
              <div className={styles.completionContainer}>
                <Tile className={styles.completionTile}>
                  <div className={styles.completionContent}>
                    <div className={styles.completionIcon}>
                      <Checkmark size={48} />
                    </div>
                    <h3 className={styles.completionTitle}>Upload Complete!</h3>
                    <p className={styles.completionMessage}>
                      Your document{files.length > 1 ? 's have' : ' has'} been successfully uploaded and processing has started.
                    </p>
                    {jobId && (
                      <div className={styles.jobIdContainer}>
                        <span className={styles.jobIdLabel}>Job ID:</span>
                        <code className={styles.jobId}>{jobId}</code>
                      </div>
                    )}
                  </div>
                  
                  <div className={styles.completionActions}>
                    <Button
                      kind="primary"
                      renderIcon={Renew}
                      onClick={handleUploadMore}
                      size="lg"
                    >
                      Upload More Documents
                    </Button>
                    <Button
                      kind="secondary"
                      renderIcon={View}
                      onClick={handleViewJobs}
                      size="lg"
                    >
                      View Running Jobs
                    </Button>
                  </div>
                </Tile>
              </div>
            ) : (
              <>
                {/* Operation Type */}
                <Tile className={styles.formTile}>
                  <div className={styles.tileHeader}>
                    <h4>Step 1: Select Operation Type</h4>
                    <p className={styles.tileDescription}>
                      Choose how you want to process your documents
                    </p>
                  </div>
                  <RadioButtonGroup
                    legendText=""
                    name="operation"
                    valueSelected={operation}
                    onChange={handleOperationChange}
                    orientation="vertical"
                  >
                    <RadioButton
                      labelText="Ingestion"
                      value="ingestion"
                      id="operation-ingestion"
                      helperText="Process documents and store in vector database for RAG applications"
                    />
                    <RadioButton
                      labelText="Digitization"
                      value="digitization"
                      id="operation-digitization"
                      helperText="Convert documents to structured format (JSON, Markdown, or Text)"
                    />
                  </RadioButtonGroup>
                </Tile>

                {/* Output Format (only for digitization) */}
                {operation === 'digitization' && (
                  <Tile className={styles.formTile}>
                    <div className={styles.tileHeader}>
                      <h4>Output Format</h4>
                      <p className={styles.tileDescription}>
                        Select the desired output format for digitized content
                      </p>
                    </div>
                    <RadioButtonGroup
                      legendText=""
                      name="outputFormat"
                      valueSelected={outputFormat}
                      onChange={(value) => setOutputFormat(value)}
                      orientation="horizontal"
                    >
                      <RadioButton
                        labelText="JSON"
                        value="json"
                        id="format-json"
                        helperText="Structured data format"
                      />
                      <RadioButton
                        labelText="Markdown"
                        value="md"
                        id="format-md"
                        helperText="Formatted text with markup"
                      />
                      <RadioButton
                        labelText="Text"
                        value="text"
                        id="format-text"
                        helperText="Plain text output"
                      />
                    </RadioButtonGroup>
                  </Tile>
                )}

                {/* File Upload */}
                <Tile className={styles.formTile}>
                  <div className={styles.tileHeader}>
                    <h4>Step 2: Upload Files</h4>
                    <p className={styles.tileDescription}>
                      {operation === 'ingestion'
                        ? 'Upload one or more PDF files (max 500MB each)'
                        : 'Upload a single PDF file (max 500MB)'}
                    </p>
                  </div>
                  <FileUploader
                    key={fileUploaderKey}
                    labelTitle=""
                    labelDescription="Drag and drop files here or click to browse"
                    buttonLabel="Select files"
                    filenameStatus="edit"
                    accept={['.pdf']}
                    multiple={operation === 'ingestion'}
                    onChange={handleFileChange}
                    size="lg"
                    className={styles.fileUploader}
                  />
                </Tile>

                {/* Selected Files Display */}
                {files.length > 0 && (
                  <Tile className={styles.fileListTile}>
                    <div
                      className={styles.fileListHeader}
                      onClick={() => setIsFileListExpanded(!isFileListExpanded)}
                      role="button"
                      tabIndex={0}
                    >
                      <DocumentPdf size={24} />
                      <h4>Selected Files ({files.length})</h4>
                      <span className={`${styles.expandIcon} ${isFileListExpanded ? styles.expanded : ''}`}>
                        ▼
                      </span>
                    </div>
                    {isFileListExpanded && (
                      <ul className={styles.fileList}>
                        {files.map((file, index) => (
                          <li key={index} className={styles.fileItem}>
                            <DocumentPdf size={20} className={styles.fileIcon} />
                            <span className={styles.fileName}>{file.name}</span>
                            <span className={styles.fileSize}>
                              ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                            <button
                              className={styles.removeButton}
                              onClick={(e) => {
                                e.stopPropagation();
                                const newFiles = files.filter((_, i) => i !== index);
                                setFiles(newFiles);
                                if (newFiles.length === 0) {
                                  setCurrentStep(1);
                                  setFileUploaderKey(prev => prev + 1);
                                }
                              }}
                              aria-label="Remove file"
                              title="Remove file"
                            >
                              <Close size={16} />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Tile>
                )}

                {/* Notifications */}
                {error && (
                  <InlineNotification
                    kind="error"
                    title="Upload Error"
                    subtitle={error}
                    onCloseButtonClick={() => setError(null)}
                    className={styles.notification}
                    lowContrast
                  />
                )}

                {success && !isCompleted && (
                  <InlineNotification
                    kind="success"
                    title="Upload Successful"
                    subtitle={success}
                    onCloseButtonClick={() => setSuccess(null)}
                    className={styles.notification}
                    lowContrast
                  />
                )}

                {/* Action Buttons */}
                <div className={styles.actionButtons}>
                  <Button
                    kind="primary"
                    renderIcon={Upload}
                    onClick={handleUpload}
                    disabled={loading || files.length === 0}
                    size="lg"
                  >
                    {loading ? 'Processing...' : 'Upload and Process'}
                  </Button>
                  {files.length > 0 && !loading && (
                    <Button
                      kind="secondary"
                      onClick={() => {
                        setFiles([]);
                        setCurrentStep(1);
                        setFileUploaderKey(prev => prev + 1);
                      }}
                      size="lg"
                    >
                      Clear Selection
                    </Button>
                  )}
                </div>

                {loading && (
                  <div className={styles.loadingContainer}>
                    <Loading description="Uploading and processing documents..." withOverlay={false} />
                  </div>
                )}
              </>
            )}
          </div>
        </Column>

        {/* Right Column - Info Panel */}
        <Column lg={6} md={2} sm={4}>
          <div className={styles.infoPanel}>
            <Accordion>
              <AccordionItem title="About Document Processing" open={false}>
                <div className={styles.accordionContent}>
                  <div className={styles.infoSection}>
                    <h5>Ingestion</h5>
                    <p>
                      Processes documents using advanced AI to extract text, tables, and structure.
                      Stores embeddings in a vector database for semantic search and RAG applications.
                    </p>
                  </div>
                  <div className={styles.infoSection}>
                    <h5>Digitization</h5>
                    <p>
                      Converts PDF documents into structured formats (JSON, Markdown, or Text)
                      while preserving document structure, tables, and formatting.
                    </p>
                  </div>
                </div>
              </AccordionItem>

              <AccordionItem title="Supported Features" open={false}>
                <div className={styles.accordionContent}>
                  <ul className={styles.featureList}>
                    <li>✓ Text extraction with layout preservation</li>
                    <li>✓ Table detection and extraction</li>
                    <li>✓ Multi-column document support</li>
                    <li>✓ Header and footer detection</li>
                    <li>✓ Image and figure recognition</li>
                    <li>✓ Batch processing support</li>
                  </ul>
                </div>
              </AccordionItem>

              <AccordionItem title="File Requirements" open={false}>
                <div className={styles.accordionContent}>
                  <ul className={styles.requirementsList}>
                    <li><strong>Format:</strong> PDF only</li>
                    <li><strong>Max Size:</strong> 500MB per file</li>
                    <li><strong>Ingestion:</strong> Multiple files allowed</li>
                    <li><strong>Digitization:</strong> Single file only</li>
                  </ul>
                </div>
              </AccordionItem>
            </Accordion>
          </div>
        </Column>
      </Grid>
    </>
  );
};

export default DocumentUploadPage;

// Made with Bob
