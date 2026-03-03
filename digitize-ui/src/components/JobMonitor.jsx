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
  Search,
  Dropdown,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { getAllJobs, getJobById } from '../services/api';
import styles from './JobMonitor.module.scss';

const headers = [
  { key: 'job_id', header: 'Job ID' },
  { key: 'operation', header: 'Operation' },
  { key: 'status', header: 'Status' },
  { key: 'documents', header: 'Documents' },
  { key: 'submitted_at', header: 'Submitted At' },
  { key: 'actions', header: '' },
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
  const [pageSize, setPageSize] = useState(25);
  const [totalItems, setTotalItems] = useState(0);
  const [selectedJob, setSelectedJob] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [operationFilter, setOperationFilter] = useState('all');

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

  const getStatusDisplay = (status) => {
    const statusMap = {
      'completed': { label: 'Completed', className: 'normal' },
      'failed': { label: 'Failed', className: 'error' },
      'in_progress': { label: 'In Progress', className: 'inProgress' },
      'accepted': { label: 'Accepted', className: 'warning' },
    };
    const statusInfo = statusMap[status] || { label: status, className: 'normal' };
    
    return (
      <div className={styles.statusIndicator}>
        <span className={`${styles.dot} ${styles[statusInfo.className]}`}></span>
        <span>{statusInfo.label}</span>
      </div>
    );
  };

  // Filter jobs based on search, operation, and status
  const filteredJobs = jobs.filter((job) => {
    // Search filter
    const matchesSearch = searchValue === '' ||
      job.job_id?.toLowerCase().includes(searchValue.toLowerCase()) ||
      job.operation?.toLowerCase().includes(searchValue.toLowerCase()) ||
      job.documents?.some(doc => doc.name?.toLowerCase().includes(searchValue.toLowerCase()));

    // Operation filter
    const matchesOperation = operationFilter === 'all' || job.operation === operationFilter;

    // Status filter
    const matchesStatus = statusFilter === 'all' || job.status === statusFilter;

    return matchesSearch && matchesOperation && matchesStatus;
  });

  const rows = filteredJobs.map((job) => ({
    id: job.job_id,
    job_id: (
      <span className={styles.jobId}>
        {job.job_id}
      </span>
    ),
    operation: (
      <Tag size="sm" {...getOperationTagType(job.operation)}>
        {job.operation}
      </Tag>
    ),
    status: getStatusDisplay(job.status),
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
    <div className={styles.jobMonitor}>
      <div className={styles.header}>
        <h1>Jobs</h1>
        
        <div className={styles.toolbar}>
          <div className={styles.filterGroup}>
            <Dropdown
              id="operation-filter"
              titleText=""
              label="Operation"
              items={[
                { id: 'all', text: 'All Operations' },
                { id: 'ingestion', text: 'Ingestion' },
                { id: 'digitization', text: 'Digitization' },
              ]}
              itemToString={(item) => (item ? item.text : '')}
              selectedItem={
                operationFilter === 'all'
                  ? { id: 'all', text: 'All Operations' }
                  : { id: operationFilter, text: operationFilter.charAt(0).toUpperCase() + operationFilter.slice(1) }
              }
              onChange={({ selectedItem }) => setOperationFilter(selectedItem.id)}
            />
            
            <Dropdown
              id="status-filter"
              titleText=""
              label="Status"
              items={[
                { id: 'all', text: 'All Status' },
                { id: 'accepted', text: 'Accepted' },
                { id: 'in_progress', text: 'In Progress' },
                { id: 'completed', text: 'Completed' },
                { id: 'failed', text: 'Failed' },
              ]}
              itemToString={(item) => (item ? item.text : '')}
              selectedItem={
                statusFilter === 'all'
                  ? { id: 'all', text: 'All Status' }
                  : { id: statusFilter, text: statusFilter.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') }
              }
              onChange={({ selectedItem }) => setStatusFilter(selectedItem.id)}
            />
          </div>

          <div className={styles.searchWrapper}>
            <Search
              size="lg"
              placeholder="Search"
              labelText="Search"
              closeButtonLabelText="Clear search input"
              id="search-jobs"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
            />
          </div>

          <div className={styles.actions}>
            <Button
              kind="primary"
              size="lg"
              renderIcon={Renew}
              hasIconOnly
              iconDescription="Refresh"
              onClick={handleRefresh}
              disabled={loading}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <Loading description="Loading jobs..." />
      ) : (
        <div className={styles.tableWrapper}>
          <DataTable rows={rows} headers={headers} size="lg">
            {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
              <>
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
                            <div className={styles.emptyState}>
                              No jobs found. Upload documents to create jobs.
                            </div>
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

                {totalItems > pageSize && (
                  <Pagination
                    backwardText="Previous page"
                    forwardText="Next page"
                    itemsPerPageText="Items per page:"
                    page={page}
                    pageSize={pageSize}
                    pageSizes={[25, 50, 100]}
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
          <div className={styles.modalContent}>
            <div className={styles.detailRow}>
              <strong>Job ID:</strong>
              <span className={styles.jobId}>{selectedJob.job_id}</span>
            </div>
            <div className={styles.detailRow}>
              <strong>Operation:</strong>
              <span>{selectedJob.operation}</span>
            </div>
            <div className={styles.detailRow}>
              <strong>Status:</strong>
              {getStatusDisplay(selectedJob.status)}
            </div>
            <div className={styles.detailRow}>
              <strong>Submitted At:</strong>
              <span>
                {selectedJob.submitted_at
                  ? new Date(selectedJob.submitted_at).toLocaleString()
                  : 'N/A'}
              </span>
            </div>
            {selectedJob.error && (
              <div className={styles.errorMessage}>
                <strong>Error:</strong> {selectedJob.error}
              </div>
            )}
            <div className={styles.detailRow}>
              <strong>Documents:</strong>
              <div>
                {selectedJob.documents && selectedJob.documents.length > 0 ? (
                  <div>
                    {selectedJob.documents.map((doc, idx) => (
                      <div key={idx} className={styles.documentCard}>
                        <div className={styles.documentDetail}>
                          <strong>Name:</strong> {doc.name}
                        </div>
                        <div className={styles.documentDetail}>
                          <strong>ID:</strong> {doc.id}
                        </div>
                        <div className={styles.documentDetail}>
                          <strong>Status:</strong> {getStatusDisplay(doc.status)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div>No documents</div>
                )}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default JobMonitor;

// Made with Bob
