package validator

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"go.yaml.in/yaml/v3"
)

// ValidationRule represents a single validation rule extracted from YAML comments
type ValidationRule struct {
	Type  string
	Value string
}

// FieldValidator holds all validation rules for a specific field
type FieldValidator struct {
	Path  string
	Rules []ValidationRule
}

// ValidatorConfig holds all field validators for a values.yaml file
type ValidatorConfig struct {
	Validators map[string]*FieldValidator // key is the dotted path like "ui.port"
}

// ParseValidators extracts validation rules from YAML node comments
func ParseValidators(data []byte) (*ValidatorConfig, error) {
	var root yaml.Node
	if err := yaml.Unmarshal(data, &root); err != nil {
		return nil, fmt.Errorf("failed to unmarshal yaml: %w", err)
	}

	config := &ValidatorConfig{
		Validators: make(map[string]*FieldValidator),
	}

	if len(root.Content) > 0 {
		parseNode("", root.Content[0], config)
	}

	return config, nil
}

// parseNode recursively traverses YAML nodes to extract validators
func parseNode(prefix string, n *yaml.Node, config *ValidatorConfig) {
	if n == nil {
		return
	}

	switch n.Kind {
	case yaml.MappingNode:
		for i := 0; i+1 < len(n.Content); i += 2 {
			keyNode := n.Content[i]
			valNode := n.Content[i+1]

			newPrefix := joinPrefix(prefix, keyNode.Value)

			// Extract validators from the key node's head comment
			rules := extractValidationRules(keyNode.HeadComment)
			if len(rules) > 0 {
				config.Validators[newPrefix] = &FieldValidator{
					Path:  newPrefix,
					Rules: rules,
				}
			}

			parseNode(newPrefix, valNode, config)
		}
	case yaml.SequenceNode:
		for i, el := range n.Content {
			newPrefix := fmt.Sprintf("%s[%d]", prefix, i)
			parseNode(newPrefix, el, config)
		}
	}
}

// extractValidationRules parses @validator annotations from comments
func extractValidationRules(comment string) []ValidationRule {
	var rules []ValidationRule

	lines := strings.Split(comment, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if !strings.Contains(line, "@validator") {
			continue
		}

		// Extract the validator directive
		idx := strings.Index(line, "@validator")
		if idx < 0 {
			continue
		}

		directive := strings.TrimSpace(line[idx+len("@validator"):])

		// Parse "key: value" format
		parts := strings.SplitN(directive, ":", 2)
		if len(parts) != 2 {
			continue
		}

		ruleType := strings.TrimSpace(parts[0])
		ruleValue := strings.TrimSpace(parts[1])

		rules = append(rules, ValidationRule{
			Type:  ruleType,
			Value: ruleValue,
		})
	}

	return rules
}

// ValidateValues validates the provided values against the validator config
func (vc *ValidatorConfig) ValidateValues(values map[string]interface{}) error {
	for path, validator := range vc.Validators {
		value := getNestedValue(values, path)

		if err := validator.Validate(value); err != nil {
			return fmt.Errorf("validation failed for '%s': %w", path, err)
		}
	}

	return nil
}

// Validate applies all rules to a value
func (fv *FieldValidator) Validate(value interface{}) error {
	for _, rule := range fv.Rules {
		if err := applyRule(rule, value); err != nil {
			return err
		}
	}

	return nil
}

// applyRule applies a single validation rule
func applyRule(rule ValidationRule, value interface{}) error {
	switch rule.Type {
	case "required":
		return validateRequired(rule.Value, value)
	case "integer":
		return validateInteger(rule.Value, value)
	case "min":
		return validateMin(rule.Value, value)
	case "max":
		return validateMax(rule.Value, value)
	case "pattern":
		return validatePattern(rule.Value, value)
	case "minLength":
		return validateMinLength(rule.Value, value)
	default:
		// Unknown validator types are ignored (for forward compatibility)
		return nil
	}
}

// validateRequired checks if a value is present
func validateRequired(ruleValue string, value interface{}) error {
	if ruleValue != "true" {
		return nil
	}

	if value == nil {
		return fmt.Errorf("field is required but not provided")
	}

	// Check for empty strings
	if str, ok := value.(string); ok && str == "" {
		return fmt.Errorf("field is required but empty")
	}

	return nil
}

// validateInteger checks if a value is an integer
func validateInteger(ruleValue string, value interface{}) error {
	if ruleValue != "true" {
		return nil
	}

	if value == nil {
		return nil // Skip validation for nil values (use required for that)
	}

	str, ok := value.(string)
	if !ok {
		// If it's already an int, that's fine
		if _, ok := value.(int); ok {
			return nil
		}
		if _, ok := value.(int64); ok {
			return nil
		}
		return fmt.Errorf("value must be an integer, got %T", value)
	}

	// Allow empty strings (use required to enforce non-empty)
	if str == "" {
		return nil
	}

	if _, err := strconv.Atoi(str); err != nil {
		return fmt.Errorf("value '%s' is not a valid integer", str)
	}

	return nil
}

// validateMin checks if a numeric value meets minimum requirement
func validateMin(ruleValue string, value interface{}) error {
	if value == nil {
		return nil
	}

	minVal, err := strconv.Atoi(ruleValue)
	if err != nil {
		return fmt.Errorf("invalid min rule value: %s", ruleValue)
	}

	var intVal int
	switch v := value.(type) {
	case string:
		if v == "" {
			return nil // Skip empty strings
		}
		intVal, err = strconv.Atoi(v)
		if err != nil {
			return fmt.Errorf("cannot validate min on non-numeric value: %s", v)
		}
	case int:
		intVal = v
	case int64:
		intVal = int(v)
	default:
		return nil // Skip validation for non-numeric types
	}

	if intVal < minVal {
		return fmt.Errorf("value %d is less than minimum %d", intVal, minVal)
	}

	return nil
}

// validateMax checks if a numeric value meets maximum requirement
func validateMax(ruleValue string, value interface{}) error {
	if value == nil {
		return nil
	}

	maxVal, err := strconv.Atoi(ruleValue)
	if err != nil {
		return fmt.Errorf("invalid max rule value: %s", ruleValue)
	}

	var intVal int
	switch v := value.(type) {
	case string:
		if v == "" {
			return nil // Skip empty strings
		}
		intVal, err = strconv.Atoi(v)
		if err != nil {
			return fmt.Errorf("cannot validate max on non-numeric value: %s", v)
		}
	case int:
		intVal = v
	case int64:
		intVal = int(v)
	default:
		return nil // Skip validation for non-numeric types
	}

	if intVal > maxVal {
		return fmt.Errorf("value %d exceeds maximum %d", intVal, maxVal)
	}

	return nil
}

// validatePattern checks if a string matches a regex pattern
func validatePattern(ruleValue string, value interface{}) error {
	if value == nil {
		return nil
	}

	str, ok := value.(string)
	if !ok {
		return fmt.Errorf("pattern validation requires string value, got %T", value)
	}

	if str == "" {
		return nil // Skip empty strings
	}

	matched, err := regexp.MatchString(ruleValue, str)
	if err != nil {
		return fmt.Errorf("invalid regex pattern: %s", ruleValue)
	}

	if !matched {
		return fmt.Errorf("value '%s' does not match required pattern '%s'", str, ruleValue)
	}

	return nil
}

// validateMinLength checks if a string meets minimum length requirement
func validateMinLength(ruleValue string, value interface{}) error {
	if value == nil {
		return nil
	}

	minLen, err := strconv.Atoi(ruleValue)
	if err != nil {
		return fmt.Errorf("invalid minLength rule value: %s", ruleValue)
	}

	str, ok := value.(string)
	if !ok {
		return fmt.Errorf("minLength validation requires string value, got %T", value)
	}

	if str == "" {
		return nil // Skip empty strings (use required for that)
	}

	if len(str) < minLen {
		return fmt.Errorf("value length %d is less than minimum length %d", len(str), minLen)
	}

	return nil
}

// getNestedValue retrieves a value from a nested map using dotted notation
func getNestedValue(m map[string]interface{}, path string) interface{} {
	parts := strings.Split(path, ".")
	current := m

	for i, key := range parts {
		val, ok := current[key]
		if !ok {
			return nil
		}

		if i == len(parts)-1 {
			return val
		}

		current, ok = val.(map[string]interface{})
		if !ok {
			return nil
		}
	}

	return nil
}

// joinPrefix creates a dotted path
func joinPrefix(prefix, key string) string {
	if prefix == "" {
		return key
	}
	return prefix + "." + key
}

// Made with Bob
