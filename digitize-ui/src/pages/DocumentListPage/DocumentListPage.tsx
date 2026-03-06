import { useState, useEffect } from 'react';
import { NoDataEmptyState } from '@carbon/ibm-products';
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
  TableToolbarSearch,
  TableToolbarMenu,
  TableToolbarAction,
  TableBatchActions,
  TableBatchAction,
  TableSelectAll,
  TableSelectRow,
  Pagination,
  Button,
  Tag,
  Modal,
  Theme,
  Link,
} from '@carbon/react';
import { Renew, TrashCan, View, Download, CheckmarkFilled, ErrorFilled, InProgress } from '@carbon/icons-react';
import { useTheme } from '../../contexts/ThemeContext';
import { listDocuments, getDocumentContent, deleteDocument, Document } from '../../services/api';
import styles from './DocumentListPage.module.scss';

const headers = [
  { key: 'name', header: 'Document name' },
  { key: 'status', header: 'Status' },
  { key: 'created_at', header: 'Created' },
  { key: 'actions', header: '' },
];

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckmarkFilled size={16} className={styles.statusIconSuccess} />;
    case 'failed':
      return <ErrorFilled size={16} className={styles.statusIconError} />;
    case 'processing':
      return <InProgress size={16} className={styles.statusIconProgress} />;
    default:
      return null;
  }
};

const DocumentListPage = () => {
  const { effectiveTheme } = useTheme();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [showContentModal, setShowContentModal] = useState<boolean>(false);
  const [docContent, setDocContent] = useState<any>(null);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [docToDelete, setDocToDelete] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * pageSize;
      const response = await listDocuments({
        limit: pageSize,
        offset: offset,
        name: search || null,
      });
      
      const docs = response.data || [];
      setDocuments(docs);
      setTotalItems(response.pagination?.total || 0);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [page, pageSize, search]);

  const handleViewContent = async (docId: string) => {
    try {
      const content = await getDocumentContent(docId);
      setDocContent(content);
      setSelectedDoc(docId);
      setShowContentModal(true);
    } catch (error) {
      console.error('Error fetching document content:', error);
    }
  };

  const handleDeleteClick = (docId: string) => {
    setDocToDelete(docId);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    if (!docToDelete) return;
    try {
      await deleteDocument(docToDelete);
      setShowDeleteModal(false);
      setDocToDelete(null);
      fetchDocuments();
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  const rows = documents.map((doc) => ({
    id: doc.id,
    name: doc.name || doc.filename || 'N/A',
    status: (
      <div className={styles.statusCell}>
        {getStatusIcon(doc.status)}
        <span className={styles.statusText}>{doc.status}</span>
      </div>
    ),
    created_at: doc.created_at
      ? new Date(doc.created_at).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          hour12: true,
        })
      : 'N/A',
    actions: (
      <Button
        kind="ghost"
        size="sm"
        onClick={() => handleViewContent(doc.id)}
      >
        View content
      </Button>
    ),
  }));

  const noDocuments = documents.length === 0 && !search;
  const noSearchResults = documents.length === 0 && search;

  const handleDeleteJobs = async (selectedRows: any[]) => {
    try {
      const docIds = selectedRows.map(row => row.id);
      
      for (const docId of docIds) {
        await deleteDocument(docId);
      }
      
      fetchDocuments();
    } catch (error) {
      console.error('Error deleting documents:', error);
    }
  };

  return (
    <Theme theme={effectiveTheme}>
      <div className={styles.documentListPage}>
        {/* Page Header */}
        <div className={styles.pageHeader}>
          <div className={styles.headerContent}>
            <h1 className={styles.pageTitle}>Documents</h1>
            <Link href="#" className={styles.learnMore}>
              Learn more →
            </Link>
          </div>
        </div>

        {/* Data Table with Enhanced Toolbar */}
        <div className={styles.tableWrapper}>
          <DataTable rows={rows} headers={headers} size="lg">
            {({
              rows,
              headers,
              getHeaderProps,
              getRowProps,
              getTableProps,
              getSelectionProps,
              getToolbarProps,
              getBatchActionProps,
              selectedRows,
              getTableContainerProps,
            }) => {
              const batchActionProps = getBatchActionProps();
              
              return (
                <TableContainer
                  {...getTableContainerProps()}
                  className={styles.tableContainer}
                >
                  <TableToolbar {...getToolbarProps()}>
                    <TableBatchActions {...batchActionProps}>
                      <TableBatchAction
                        tabIndex={batchActionProps.shouldShowBatchActions ? 0 : -1}
                        renderIcon={TrashCan}
                        onClick={() => handleDeleteJobs(selectedRows)}
                      >
                        Delete
                      </TableBatchAction>
                    </TableBatchActions>
                    <TableToolbarContent>
                      <TableToolbarSearch
                        persistent
                        placeholder="Search"
                        onChange={(e: any, value?: string) => setSearch(value || '')}
                        value={search}
                      />
                      <Button
                        kind="ghost"
                        hasIconOnly
                        renderIcon={Download}
                        iconDescription="Download"
                        tooltipPosition="bottom"
                      />
                      <Button
                        kind="ghost"
                        hasIconOnly
                        renderIcon={Renew}
                        iconDescription="Refresh"
                        onClick={fetchDocuments}
                        disabled={loading}
                        tooltipPosition="bottom"
                      />
                    </TableToolbarContent>
                  </TableToolbar>
                  <Table {...getTableProps()} className={styles.table}>
                    <TableHead>
                      <TableRow>
                        <TableSelectAll {...getSelectionProps()} />
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
                          <TableCell colSpan={headers.length + 1} className={styles.emptyStateCell}>
                            <NoDataEmptyState
                              illustrationTheme="light"
                              size="lg"
                              title={noSearchResults ? "No data" : "No documents found"}
                              subtitle={noSearchResults ? "Try adjusting your search." : "Start ingesting the document to get started"}
                            />
                          </TableCell>
                        </TableRow>
                      ) : (
                        rows.map((row) => {
                          const { key: rowKey, ...rowProps } = getRowProps({ row });
                          return (
                            <TableRow key={rowKey} {...rowProps}>
                              <TableSelectRow {...getSelectionProps({ row })} />
                              {row.cells.map((cell) => (
                                <TableCell key={cell.id}>{cell.value}</TableCell>
                              ))}
                            </TableRow>
                          );
                        })
                      )}
                    </TableBody>
                  </Table>
                  {rows.length > 0 && (
                    <Pagination
                      page={page}
                      pageSize={pageSize}
                      pageSizes={[10, 25, 50, 100]}
                      totalItems={totalItems}
                      onChange={({ page, pageSize }) => {
                        setPage(page);
                        setPageSize(pageSize);
                      }}
                      itemsPerPageText="Items per page:"
                    />
                  )}
                </TableContainer>
              );
            }}
          </DataTable>
        </div>

      {/* Content Modal */}
      <Modal
        open={showContentModal}
        onRequestClose={() => setShowContentModal(false)}
        modalHeading={`Document Content: ${selectedDoc}`}
        primaryButtonText="Close"
        onRequestSubmit={() => setShowContentModal(false)}
        size="lg"
      >
        <div className={styles.modalContent}>
          <pre>
            {docContent ? JSON.stringify(docContent, null, 2) : 'Loading...'}
          </pre>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={showDeleteModal}
        danger
        onRequestClose={() => setShowDeleteModal(false)}
        modalHeading="Delete Document"
        primaryButtonText="Delete"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleDeleteConfirm}
        onSecondarySubmit={() => setShowDeleteModal(false)}
      >
        <p>Are you sure you want to delete this document? This action cannot be undone.</p>
      </Modal>
    </div>
    </Theme>
  );
};

export default DocumentListPage;

// Made with Bob
