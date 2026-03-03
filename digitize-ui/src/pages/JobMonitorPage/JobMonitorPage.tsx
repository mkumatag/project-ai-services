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
  Pagination,
  Button,
  Tag,
  Grid,
  Column,
  Modal,
  Search,
  Dropdown,
  Theme,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { useTheme } from '../../contexts/ThemeContext';
import { getAllJobs, getJobById, Job, Document } from '../../services/api';
import styles from './JobMonitorPage.module.scss';

const headers = [
  { key: 'job_id', header: 'Job ID' },
  { key: 'operation', header: 'Operation' },
  { key: 'status', header: 'Status' },
  { key: 'documents', header: 'Documents' },
  { key: 'submitted_at', header: 'Submitted At' },
  { key: 'actions', header: 'Actions' },
];

const getStatusTagType = (status: string) => {
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

const getOperationTagType = (operation: string) => {
  switch (operation) {
    case 'ingestion':
      return { type: 'blue' };
    case 'digitization':
      return { type: 'purple' };
    default:
      return { type: 'cool-gray' };
  }
};

const getDocumentTagType = (status: string) => {
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
  const { effectiveTheme } = useTheme();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [searchValue, setSearchValue] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [operationFilter, setOperationFilter] = useState<string>('all');

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

  const handleViewDetails = async (jobId: string) => {
    try {
      const jobDetails = await getJobById(jobId);
      setSelectedJob(jobDetails);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error fetching job details:', error);
    }
  };

  const formatDocuments = (documents: Document[] | undefined) => {
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
    <Theme theme={effectiveTheme}>
      <div className={styles.jobMonitorPage}>
        <PageHeader
          title={{ text: 'Job Monitor' }}
          subtitle="Track the status of document processing jobs"
        />

      <div className={styles.content}>
        {/* Toolbar with filters and search */}
        <div className={styles.toolbar}>
          <div className={styles.filterGroup}>
            <Dropdown
              id="operation-filter"
              titleText=""
              label="Operation"
              size="lg"
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
              onChange={({ selectedItem }) => selectedItem && setOperationFilter(selectedItem.id)}
            />
            
            <Dropdown
              id="status-filter"
              titleText=""
              label="Status"
              size="lg"
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
              onChange={({ selectedItem }) => selectedItem && setStatusFilter(selectedItem.id)}
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
              onClick={fetchJobs}
              disabled={loading}
            />
          </div>
        </div>

        <Grid fullWidth>
          <Column lg={16} md={8} sm={4}>
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
          </Column>
        </Grid>
      </div>

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
    </Theme>
  );
};

export default JobMonitorPage;

// Made with Bob
