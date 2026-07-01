Day N:

{{- if ne .UI_URL "" }}
{{- if eq .UI_STATUS "running" }}

- {{ .SERVICE_NAME }} is available at {{ .UI_URL }}. Open it in a browser to send prompts to the LLM.
{{- else }}

- {{ .SERVICE_NAME }} is unavailable. Please make sure the 'hello-world' pod is running.
{{- end }}
{{- end }}
