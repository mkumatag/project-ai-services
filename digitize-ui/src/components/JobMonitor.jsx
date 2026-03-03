import { useState, useEffect } from 'react';
import {
  DataTable,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Button,
  Tag,
  Pagination,
  Loading,
  Modal,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { getAllJobs, getJobById } from '../services/api';

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

const JobMonitor = ({ refreshTrigger }) => {
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
  }, [page, pageSize, refreshTrigger]);

  const handleRefresh = () => {
    fetchJobs();
  };

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
        {documents.slice(0, 2).map((doc, idx) => (
          <div key={idx} style={{ marginBottom: '4px' }}>
            <Tag {...getDocumentTagType(doc.status)} size="sm">
              {doc.name}
            </Tag>
          </div>
        ))}
        {documents.length > 2 && (
          <span style={{ fontSize: '0.75rem', color: '#525252' }}>
            +{documents.length - 2} more
          </span>
        )}
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
        kind="ghost"
        size="sm"
        onClick={() => handleViewDetails(job.job_id)}
      >
        View Details
      </Button>
    ),
  }));

  return (
    <div className="job-monitor">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>Job Monitor</h3>
        <Button
          renderIcon={Renew}
          kind="tertiary"
          size="sm"
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      {loading ? (
        <Loading description="Loading jobs..." />
      ) : (
        <>
          <DataTable rows={rows} headers={headers}>
            {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
              <TableContainer>
                <Table {...getTableProps()}>
                  <TableHead>
                    <TableRow>
                      {headers.map((header) => (
                        <TableHeader {...getHeaderProps({ header })} key={header.key}>
                          {header.header}
                        </TableHeader>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={headers.length}>
                          No jobs found. Upload documents to create jobs.
                        </TableCell>
                      </TableRow>
                    ) : (
                      rows.map((row) => (
                        <TableRow {...getRowProps({ row })} key={row.id}>
                          {row.cells.map((cell) => (
                            <TableCell key={cell.id}>{cell.value}</TableCell>
                          ))}
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DataTable>

          {totalItems > pageSize && (
            <Pagination
              backwardText="Previous page"
              forwardText="Next page"
              itemsPerPageText="Items per page:"
              page={page}
              pageSize={pageSize}
              pageSizes={[10, 20, 30, 40, 50]}
              totalItems={totalItems}
              onChange={({ page, pageSize }) => {
                setPage(page);
                setPageSize(pageSize);
              }}
            />
          )}
        </>
      )}

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
    </div>
  );
};

export default JobMonitor;

// Made with Bob
