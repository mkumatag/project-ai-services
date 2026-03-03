import axios from 'axios';

const API_BASE_URL = '/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Document Upload and Processing
export const uploadDocuments = async (files, operation = 'ingestion', outputFormat = 'json') => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await api.post(
    `/documents?operation=${operation}&output_format=${outputFormat}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

// Job Management
export const getAllJobs = async (params = {}) => {
  const { latest = false, limit = 20, offset = 0, status = null } = params;
  const queryParams = new URLSearchParams({
    latest: latest.toString(),
    limit: limit.toString(),
    offset: offset.toString(),
  });
  
  if (status) {
    queryParams.append('status', status);
  }

  const response = await api.get(`/documents/jobs?${queryParams}`);
  return response.data;
};

export const getJobById = async (jobId) => {
  const response = await api.get(`/documents/jobs/${jobId}`);
  return response.data;
};

// Document Management
export const listDocuments = async (params = {}) => {
  const { limit = 20, offset = 0, status = null, name = null } = params;
  const queryParams = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  
  if (status) {
    queryParams.append('status', status);
  }
  if (name) {
    queryParams.append('name', name);
  }

  const response = await api.get(`/documents?${queryParams}`);
  return response.data;
};

export const getDocumentMetadata = async (docId, details = false) => {
  const response = await api.get(`/documents/${docId}?details=${details}`);
  return response.data;
};

export const getDocumentContent = async (docId) => {
  const response = await api.get(`/documents/${docId}/content`);
  return response.data;
};

export const deleteDocument = async (docId) => {
  const response = await api.delete(`/documents/${docId}`);
  return response.data;
};

export const bulkDeleteDocuments = async () => {
  const response = await api.delete('/documents?confirm=true');
  return response.data;
};

export default api;

// Made with Bob
