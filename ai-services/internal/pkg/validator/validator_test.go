package validator

import (
	"testing"
)

func TestValidateInteger(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"valid integer string", "true", "8080", false},
		{"valid integer", "true", 8080, false},
		{"empty string allowed", "true", "", false},
		{"invalid integer string", "true", "abc", true},
		{"nil value allowed", "true", nil, false},
		{"rule disabled", "false", "abc", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateInteger(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateInteger() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateMin(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"valid min", "0", "8080", false},
		{"valid min int", "0", 8080, false},
		{"below min", "100", "50", true},
		{"at min", "100", "100", false},
		{"empty string allowed", "0", "", false},
		{"nil allowed", "0", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateMin(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateMin() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateMax(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"valid max", "65535", "8080", false},
		{"valid max int", "65535", 8080, false},
		{"above max", "100", "150", true},
		{"at max", "100", "100", false},
		{"empty string allowed", "65535", "", false},
		{"nil allowed", "65535", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateMax(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateMax() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidatePattern(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"valid pattern", `^[0-9]+(\.[0-9]+)?(Mi|Gi|Ti)$`, "4Gi", false},
		{"valid pattern decimal", `^[0-9]+(\.[0-9]+)?(Mi|Gi|Ti)$`, "2.5Gi", false},
		{"invalid pattern", `^[0-9]+(\.[0-9]+)?(Mi|Gi|Ti)$`, "4GB", true},
		{"empty string allowed", `^[0-9]+$`, "", false},
		{"nil allowed", `^[0-9]+$`, nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validatePattern(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validatePattern() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateRequired(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"value present", "true", "admin", false},
		{"nil value", "true", nil, true},
		{"empty string", "true", "", true},
		{"rule disabled", "false", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateRequired(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateRequired() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateMinLength(t *testing.T) {
	tests := []struct {
		name      string
		ruleValue string
		value     interface{}
		wantErr   bool
	}{
		{"valid length", "3", "admin", false},
		{"at min length", "5", "admin", false},
		{"below min length", "10", "admin", true},
		{"empty string allowed", "3", "", false},
		{"nil allowed", "3", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateMinLength(tt.ruleValue, tt.value)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateMinLength() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestParseValidators(t *testing.T) {
	yamlData := []byte(`
ui:
  # @description Host port for the RAG UI
  # @validator integer: true
  # @validator min: 0
  # @validator max: 65535
  port: ""

opensearch:
  # @validator required: true
  # @validator minLength: 3
  username: "admin"
  # @validator required: true
  # @validator minLength: 8
  password: "AiServices@1234"
  # @validator pattern: ^[0-9]+(\.[0-9]+)?(Mi|Gi|Ti)$
  memoryLimit: 4Gi
`)

	config, err := ParseValidators(yamlData)
	if err != nil {
		t.Fatalf("ParseValidators() error = %v", err)
	}

	// Check ui.port validators
	if validator, ok := config.Validators["ui.port"]; ok {
		if len(validator.Rules) != 3 {
			t.Errorf("Expected 3 rules for ui.port, got %d", len(validator.Rules))
		}
	} else {
		t.Error("Expected validator for ui.port")
	}

	// Check opensearch.username validators
	if validator, ok := config.Validators["opensearch.username"]; ok {
		if len(validator.Rules) != 2 {
			t.Errorf("Expected 2 rules for opensearch.username, got %d", len(validator.Rules))
		}
	} else {
		t.Error("Expected validator for opensearch.username")
	}
}

func TestValidateValues(t *testing.T) {
	yamlData := []byte(`
ui:
  # @validator integer: true
  # @validator min: 0
  # @validator max: 65535
  port: ""

backend:
  # @validator integer: true
  # @validator min: 0
  # @validator max: 65535
  port: "0"
`)

	config, err := ParseValidators(yamlData)
	if err != nil {
		t.Fatalf("ParseValidators() error = %v", err)
	}

	tests := []struct {
		name    string
		values  map[string]interface{}
		wantErr bool
	}{
		{
			name: "valid values",
			values: map[string]interface{}{
				"ui": map[string]interface{}{
					"port": "8080",
				},
				"backend": map[string]interface{}{
					"port": "0",
				},
			},
			wantErr: false,
		},
		{
			name: "invalid port - not integer",
			values: map[string]interface{}{
				"ui": map[string]interface{}{
					"port": "abc",
				},
				"backend": map[string]interface{}{
					"port": "0",
				},
			},
			wantErr: true,
		},
		{
			name: "invalid port - below min",
			values: map[string]interface{}{
				"ui": map[string]interface{}{
					"port": "-1",
				},
				"backend": map[string]interface{}{
					"port": "0",
				},
			},
			wantErr: true,
		},
		{
			name: "invalid port - above max",
			values: map[string]interface{}{
				"ui": map[string]interface{}{
					"port": "70000",
				},
				"backend": map[string]interface{}{
					"port": "0",
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := config.ValidateValues(tt.values)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateValues() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

// Made with Bob
