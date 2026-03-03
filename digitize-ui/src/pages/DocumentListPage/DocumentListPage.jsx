import { useState, useEffect } from 'react';
import { PageHeader, NoDataEmptyState } from '@carbon/ibm-products';
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
  Pagination,
  Button,
  Tag,
  Grid,
  Column,
  Modal,
  Theme,
} from '@carbon/react';
import { Renew, TrashCan, View } from '@carbon/icons-react';
import { useTheme } from '../../contexts/ThemeContext';
import { listDocuments, getDocumentContent, deleteDocument } from '../../services/api';
import styles from './DocumentListPage.module.scss';

const headers = [
  { key: 'id', header: 'Document ID' },
  { key: 'name', header: 'Name' },
  { key: 'status', header: 'Status' },
  { key: 'created_at', header: 'Created At' },
  { key: 'actions', header: '' },
];

const getStatusKind = (status) => {
  switch (status) {
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'processing':
      return 'blue';
    default:
      return 'gray';
  }
};

const DocumentListPage = () => {
  const { effectiveTheme } = useTheme();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  const [search, setSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [showContentModal, setShowContentModal] = useState(false);
  const [docContent, setDocContent] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);

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

  const handleViewContent = async (docId) => {
    try {
      const content = await getDocumentContent(docId);
      setDocContent(content);
      setSelectedDoc(docId);
      setShowContentModal(true);
    } catch (error) {
      console.error('Error fetching document content:', error);
    }
  };

  const handleDeleteClick = (docId) => {
    setDocToDelete(docId);
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
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
      <Tag type={getStatusKind(doc.status)} size="sm">
        {doc.status}
      </Tag>
    ),
    created_at: doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A',
    actions: (
      <div className={styles.rowActions}>
        <Button
          hasIconOnly
          kind="tertiary"
          size="sm"
          renderIcon={View}
          iconDescription="View content"
          onClick={() => handleViewContent(doc.id)}
        />
        <Button
          hasIconOnly
          kind="ghost"
          size="sm"
          renderIcon={TrashCan}
          iconDescription="Delete"
          onClick={() => handleDeleteClick(doc.id)}
        />
      </div>
    ),
  }));

  const noDocuments = documents.length === 0 && !search;
  const noSearchResults = documents.length === 0 && search;

  return (
    <Theme theme={effectiveTheme}>
      <div className={styles.documentListPage}>
        <PageHeader
          title={{ text: 'Documents' }}
          subtitle="View and manage processed documents"
        />

      <div className={styles.content}>
        <Grid fullWidth>
          <Column lg={16} md={8} sm={4}>
            <div className={styles.tableContent}>
            <DataTable rows={rows} headers={headers} size="lg">
              {({
                rows,
                headers,
                getHeaderProps,
                getRowProps,
                getCellProps,
                getTableProps,
              }) => (
                <>
                  <TableContainer>
                    <TableToolbar>
                      <TableToolbarSearch
                        placeholder="Search"
                        persistent
                        value={search}
                        onChange={(e) => {
                          if (typeof e !== 'string') {
                            setSearch(e.target.value);
                          }
                        }}
                      />
                      <TableToolbarContent>
                        <Button
                          hasIconOnly
                          kind="ghost"
                          renderIcon={Renew}
                          iconDescription="Refresh"
                          size="lg"
                          onClick={fetchDocuments}
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

                      {noDocuments ? (
                        <NoDataEmptyState
                          title="No documents found"
                          subtitle="Upload documents to get started."
                          className={styles.noDataContent}
                        />
                      ) : noSearchResults ? (
                        <NoDataEmptyState
                          title="No data"
                          subtitle="Try adjusting your search."
                          className={styles.noDataContent}
                        />
                      ) : (
                        <TableBody>
                          {rows.map((row) => {
                            const { key: rowKey, ...rowProps } = getRowProps({ row });
                            return (
                              <TableRow key={rowKey} {...rowProps}>
                                {row.cells.map((cell) => {
                                  const { key: cellKey, ...cellProps } = getCellProps({ cell });
                                  return (
                                    <TableCell key={cellKey} {...cellProps}>
                                      {cell.value}
                                    </TableCell>
                                  );
                                })}
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      )}
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
