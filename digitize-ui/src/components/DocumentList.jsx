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
} from '@carbon/react';
import { View, TrashCan, Renew } from '@carbon/icons-react';
import { listDocuments, getDocumentContent, deleteDocument } from '../services/api';

const headers = [
  { key: 'id', header: 'Document ID' },
  { key: 'name', header: 'Name' },
  { key: 'status', header: 'Status' },
  { key: 'created_at', header: 'Created At' },
  { key: 'actions', header: 'Actions' },
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

const DocumentList = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
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
        name: searchTerm || null,
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
  }, [page, pageSize, searchTerm, refreshTrigger]);

  const handleRefresh = () => {
    fetchDocuments();
  };

  const handleViewContent = async (docId) => {
    try {
      const content = await getDocumentContent(docId);
      setDocContent(content);
      setSelectedDoc(docId);
      setShowContentModal(true);
    } catch (error) {
      console.error('Error fetching document content:', error);
      alert('Failed to fetch document content');
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
      alert('Failed to delete document');
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
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <Button
          renderIcon={View}
          kind="ghost"
          size="sm"
          onClick={() => handleViewContent(doc.id)}
          hasIconOnly
          iconDescription="View content"
        />
        <Button
          renderIcon={TrashCan}
          kind="danger--ghost"
          size="sm"
          onClick={() => handleDeleteClick(doc.id)}
          hasIconOnly
          iconDescription="Delete document"
        />
      </div>
    ),
  }));

  return (
    <div className="document-list">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>Documents</h3>
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

      <Search
        labelText="Search documents"
        placeholder="Search by name..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onClear={() => setSearchTerm('')}
        style={{ marginBottom: '1rem' }}
      />

      {loading ? (
        <Loading description="Loading documents..." />
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
                          No documents found. Upload documents to get started.
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

      {/* Content Modal */}
      <Modal
        open={showContentModal}
        onRequestClose={() => setShowContentModal(false)}
        modalHeading={`Document Content: ${selectedDoc}`}
        primaryButtonText="Close"
        onRequestSubmit={() => setShowContentModal(false)}
        size="lg"
      >
        <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
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
  );
};

export default DocumentList;

// Made with Bob
