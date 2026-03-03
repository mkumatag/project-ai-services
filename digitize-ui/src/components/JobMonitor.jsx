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
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { getAllJobs, getJobById } from '../services/api';

const headers = [
  { key: 'job_id', header: 'Job ID' },
  { key: 'status', header: 'Status' },
  { key: 'operation', header: 'Operation' },
  { key: 'created_at', header: 'Created At' },
  { key: 'actions', header: 'Actions' },
];

const getStatusKind = (status) => {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'in_progress':
      return 'blue';
    case 'accepted':
      return 'cyan';
    default:
      return 'gray';
  }
};

const JobMonitor = ({ refreshTrigger }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalItems, setTotalItems] = useState(0);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const response = await getAllJobs({
        limit: pageSize,
        offset: offset,
      });
      
      // Mock data for demonstration since API returns empty
      const mockJobs = response.data || [];
      setJobs(mockJobs);
      setTotalItems(response.pagination?.total || 0);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [page, pageSize, refreshTrigger]);

  const handleRefresh = () => {
    fetchJobs();
  };

  const handleViewDetails = async (jobId) => {
    try {
      const jobDetails = await getJobById(jobId);
      console.log('Job details:', jobDetails);
      // You can add a modal or detail view here
      alert(`Job Details:\n${JSON.stringify(jobDetails, null, 2)}`);
    } catch (error) {
      console.error('Error fetching job details:', error);
    }
  };

  const rows = jobs.map((job) => ({
    id: job.job_id || job.id,
    job_id: job.job_id || job.id,
    status: (
      <Tag type={getStatusKind(job.status)} size="sm">
        {job.status}
      </Tag>
    ),
    operation: job.operation || 'N/A',
    created_at: job.created_at ? new Date(job.created_at).toLocaleString() : 'N/A',
    actions: (
      <Button
        kind="ghost"
        size="sm"
        onClick={() => handleViewDetails(job.job_id || job.id)}
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
    </div>
  );
};

export default JobMonitor;

// Made with Bob
