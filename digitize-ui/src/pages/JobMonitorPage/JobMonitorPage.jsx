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
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { getAllJobs, getJobById } from '../../services/api';
import styles from './JobMonitorPage.module.scss';

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

const JobMonitorPage = () => {
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
  }, [page, pageSize]);

  const handleViewDetails = async (jobId) => {
    try {
      const jobDetails = await getJobById(jobId);
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
        kind="tertiary"
        size="sm"
        onClick={() => handleViewDetails(job.job_id || job.id)}
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
                              No jobs found. Upload documents to create jobs.
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
    </>
  );
};

export default JobMonitorPage;

// Made with Bob
