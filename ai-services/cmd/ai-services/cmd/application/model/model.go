package model

import (
	"fmt"
	"slices"

	"github.com/project-ai-services/ai-services/internal/pkg/cli/helpers"
	"github.com/project-ai-services/ai-services/internal/pkg/cli/templates"
	"github.com/project-ai-services/ai-services/internal/pkg/runtime/types"
	"github.com/project-ai-services/ai-services/internal/pkg/vars"
	"github.com/spf13/cobra"
)

var ModelCmd = &cobra.Command{
	Use:   "model",
	Short: "Manage application models",
	Long:  ``,
	Args:  cobra.MaximumNArgs(0),
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		// Walk up to the root and invoke its PersistentPreRunE (initializes vars.RuntimeFactory)
		for p := cmd.Parent(); p != nil; p = p.Parent() {
			if p.Parent() == nil && p.PersistentPreRunE != nil {
				if err := p.PersistentPreRunE(p, args); err != nil {
					return err
				}
				break
			}
		}
		if vars.RuntimeFactory.GetRuntimeType() == types.RuntimeTypeOpenShift {
			return fmt.Errorf("the 'model' command is not supported for the openshift runtime")
		}
		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		return cmd.Help()
	},
}

var hiddenTemplates bool

func init() {
	ModelCmd.AddCommand(listCmd)
	ModelCmd.AddCommand(downloadCmd)
}

func models(template string) ([]string, error) {
	tp := templates.NewEmbedTemplateProvider(templates.EmbedOptions{})
	apps, err := tp.ListApplications(hiddenTemplates)
	if err != nil {
		return nil, fmt.Errorf("failed to list the applications, err: %w", err)
	}

	if !slices.Contains(apps, template) {
		return nil, fmt.Errorf("application template %s does not exist", template)
	}

	return helpers.ListModels(template, "")
}
