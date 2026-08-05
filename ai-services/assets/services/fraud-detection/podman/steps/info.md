Day N:

{{- if eq .API_STATUS "running" }}

- {{ .SERVICE_NAME }} API is available to use at {{ .API_URL }}. Use this endpoint for fraud scoring via programmatic access.
{{- else }}

- {{ .SERVICE_NAME }} API is unavailable to use. Please make sure 'fraud-detection' pod is running.
{{- end }}
