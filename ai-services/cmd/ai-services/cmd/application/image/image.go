package image

import (
	"fmt"

	"github.com/project-ai-services/ai-services/internal/pkg/runtime/types"
	"github.com/project-ai-services/ai-services/internal/pkg/vars"
	"github.com/spf13/cobra"
)

var templateName string

var ImageCmd = &cobra.Command{
	Use:   "image",
	Short: "Manage application images",
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
			return fmt.Errorf("the 'image' command is not supported for the openshift runtime")
		}
		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		return nil
	},
}

func init() {
	ImageCmd.AddCommand(listCmd)
	ImageCmd.AddCommand(pullCmd)
	ImageCmd.PersistentFlags().StringVarP(&templateName, "template", "t", "", "Application template name (Required)")
	_ = ImageCmd.MarkPersistentFlagRequired("template")
}
