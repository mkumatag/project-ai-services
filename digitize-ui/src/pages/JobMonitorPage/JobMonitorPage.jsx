import { useState, useEffect } from 'react';
import { PageHeader } from '@carbon/ibm-products';
import {
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  TableContainer,
  TableToolbar,
  TableToolbarContent,
  Pagination,
  Button,
  Tag,
  Grid,
  Column,
  Modal,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { getAllJobs, getJobById } from '../../services/api';
import styles from './JobMonitorPage.module.scss';

const headers = [
  { key: 'job_id', header: 'Job ID' },
  { key: 'operation', header: 'Operation' },
  { key: 'status', header: 'Status' },
  { key: 'documents', header: 'Documents' },
  { key: 'submitted_at', header: 'Submitted At' },
  { key: 'actions', header: 'Actions' },
];

const getStatusTagType = (status) => {
  switch (status) {
    case 'completed':
      return { type: 'green' };
    case 'failed':
      return { type: 'red' };
    case 'in_progress':
      return { type: 'blue' };
    case 'accepted':
      return { type: 'cyan' };
    default:
      return { type: 'gray' };
  }
};

const getOperationTagType = (operation) => {
  switch (operation) {
    case 'ingestion':
      return { type: 'blue' };
    case 'digitization':
      return { type: 'purple' };
    default:
      return { type: 'cool-gray' };
  }
};

const getDocumentTagType = (status) => {
  switch (status) {
    case 'completed':
      return { type: 'green' };
    case 'failed':
      return { type: 'red' };
    case 'in_progress':
      return { type: 'blue' };
    default:
      return { type: 'gray' };
  }
};

const JobMonitorPage = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  const [selectedJob, setSelectedJob] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const response = await getAllJobs({
        limit: pageSize,
        offset: offset,
      });
      
      setJobs(response.data || []);
      setTotalItems(response.pagination?.total || 0);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, [page, pageSize]);

  const handleViewDetails = async (jobId) => {
    try {
      const jobDetails = await getJobById(jobId);
      setSelectedJob(jobDetails);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error fetching job details:', error);
    }
  };

  const formatDocuments = (documents) => {
    if (!documents || documents.length === 0) return 'No documents';
    return (
      <div>
        {documents.map((doc, idx) => (
          <div key={idx} style={{ marginBottom: '4px' }}>
            <Tag {...getDocumentTagType(doc.status)} size="sm">
              {doc.name}
            </Tag>
          </div>
        ))}
      </div>
    );
  };

  const rows = jobs.map((job) => ({
    id: job.job_id,
    job_id: (
      <span style={{
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: '0.875rem',
        color: 'var(--cds-text-primary)',
        padding: '0.25rem 0.5rem',
        backgroundColor: 'var(--cds-layer-02)',
        borderRadius: '4px',
        display: 'inline-block'
      }}>
        {job.job_id}
      </span>
    ),
    operation: (
      <Tag size="sm" {...getOperationTagType(job.operation)}>
        {job.operation}
      </Tag>
    ),
    status: (
      <Tag {...getStatusTagType(job.status)} size="sm">
        {job.status.replace('_', ' ')}
      </Tag>
    ),
    documents: formatDocuments(job.documents),
    submitted_at: job.submitted_at
      ? new Date(job.submitted_at).toLocaleString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : 'N/A',
    actions: (
      <Button
        kind="tertiary"
        size="sm"
        onClick={() => handleViewDetails(job.job_id)}
      >
        View Details
      </Button>
    ),
  }));

  return (
    <>
      <PageHeader
        title={{ text: 'Job Monitor' }}
        subtitle="Track the status of document processing jobs"
      />

      <Grid fullWidth>
        <Column lg={16} md={8} sm={4}>
          <div className={styles.tableContent}>
            <DataTable rows={rows} headers={headers} size="lg">
              {({
                rows,
                headers,
                getHeaderProps,
                getRowProps,
                getTableProps,
              }) => (
                <>
                  <TableContainer>
                    <TableToolbar>
                      <TableToolbarContent>
                        <Button
                          hasIconOnly
                          kind="ghost"
                          renderIcon={Renew}
                          iconDescription="Refresh"
                          size="lg"
                          onClick={fetchJobs}
                          disabled={loading}
                        />
                      </TableToolbarContent>
                    </TableToolbar>
                    <Table {...getTableProps()}>
                      <TableHead>
                        <TableRow>
                          {headers.map((header) => {
                            const { key, ...rest } = getHeaderProps({ header });
                            return (
                              <TableHeader key={key} {...rest}>
                                {header.header}
                              </TableHeader>
                            );
                          })}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {rows.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={headers.length}>
                              {loading ? 'Loading jobs...' : 'No jobs found. Upload documents to create jobs.'}
                            </TableCell>
                          </TableRow>
                        ) : (
                          rows.map((row) => {
                            const { key: rowKey, ...rowProps } = getRowProps({ row });
                            return (
                              <TableRow key={rowKey} {...rowProps}>
                                {row.cells.map((cell) => (
                                  <TableCell key={cell.id}>{cell.value}</TableCell>
                                ))}
                              </TableRow>
                            );
                          })
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {totalItems > pageSize && (
                    <Pagination
                      page={page}
                      pageSize={pageSize}
                      pageSizes={[5, 10, 20, 30]}
                      totalItems={totalItems}
                      onChange={({ page, pageSize }) => {
                        setPage(page);
                        setPageSize(pageSize);
                      }}
                    />
                  )}
                </>
              )}
            </DataTable>
          </div>
        </Column>
      </Grid>

      {/* Job Details Modal */}
      <Modal
        open={isModalOpen}
        onRequestClose={() => setIsModalOpen(false)}
        modalHeading="Job Details"
        primaryButtonText="Close"
        onRequestSubmit={() => setIsModalOpen(false)}
        size="lg"
      >
        {selectedJob && (
          <div style={{ padding: '1rem' }}>
            <div style={{ marginBottom: '1rem' }}>
              <strong>Job ID:</strong> {selectedJob.job_id}
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>Operation:</strong> {selectedJob.operation}
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>Status:</strong>{' '}
              <Tag {...getStatusTagType(selectedJob.status)} size="sm">
                {selectedJob.status.replace('_', ' ')}
              </Tag>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>Submitted At:</strong>{' '}
              {selectedJob.submitted_at
                ? new Date(selectedJob.submitted_at).toLocaleString()
                : 'N/A'}
            </div>
            {selectedJob.error && (
              <div style={{ marginBottom: '1rem', color: '#da1e28' }}>
                <strong>Error:</strong> {selectedJob.error}
              </div>
            )}
            <div style={{ marginBottom: '1rem' }}>
              <strong>Documents:</strong>
              {selectedJob.documents && selectedJob.documents.length > 0 ? (
                <div style={{ marginTop: '0.5rem' }}>
                  {selectedJob.documents.map((doc, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.5rem',
                        marginBottom: '0.5rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '4px',
                      }}
                    >
                      <div><strong>Name:</strong> {doc.name}</div>
                      <div><strong>ID:</strong> {doc.id}</div>
                      <div>
                        <strong>Status:</strong>{' '}
                        <Tag {...getDocumentTagType(doc.status)} size="sm">
                          {doc.status}
                        </Tag>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div>No documents</div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

export default JobMonitorPage;

// Made with Bob
