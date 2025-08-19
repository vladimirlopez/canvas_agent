// src/tools/attach_rubric.ts
import { AttachRubricInput, AttachRubricInputSchema, AttachRubricInputType, CanvasRubric } from '../schemas';
import { CanvasClient } from '../canvas';

export function attachRubricTool(client: CanvasClient) {
  return {
    name: 'attach_rubric_to_assignment',
    description: 'Create a rubric and attach it to an existing assignment for structured grading',
    inputSchema: AttachRubricInputSchema,
    
    handler: async (input: AttachRubricInputType) => {
      try {
        // Validate input using Zod
        const validatedInput = AttachRubricInput.parse(input);
        
        // Step 1: Create the rubric
        const rubricData = {
          rubric: validatedInput.rubric.map((criterion: any, index: number) => ({
            id: criterion.id || `criterion_${index}`,
            points: criterion.points,
            description: criterion.description,
            long_description: criterion.long_description || '',
            ratings: criterion.ratings.map((rating: any, ratingIndex: number) => ({
              id: rating.id || `rating_${index}_${ratingIndex}`,
              description: rating.description,
              points: rating.points,
            }))
          })),
          title: validatedInput.title,
          points_possible: validatedInput.rubric.reduce((total: number, criterion: any) => total + criterion.points, 0),
          free_form_criterion_comments: validatedInput.free_form_criterion_comments,
        };

        const rubric = await client.post<CanvasRubric>(
          `/api/v1/courses/${validatedInput.course_id}/rubrics`,
          rubricData
        );

        // Step 2: Associate rubric with assignment
        const associationData = {
          rubric_association: {
            association_type: 'Assignment',
            association_id: validatedInput.assignment_id,
            rubric_id: rubric.id,
            use_for_grading: validatedInput.use_for_grading,
            purpose: 'grading',
          }
        };

        const association = await client.post<any>(
          `/api/v1/courses/${validatedInput.course_id}/rubric_associations`,
          associationData
        );

        return {
          content: [
            {
              type: 'text' as const,
              text: `✅ Successfully created and attached rubric "${validatedInput.title}"\n\n` +
                    `**Rubric Details:**\n` +
                    `- Rubric ID: ${rubric.id}\n` +
                    `- Title: ${rubric.title}\n` +
                    `- Total Points: ${rubric.points_possible}\n` +
                    `- Criteria Count: ${validatedInput.rubric.length}\n` +
                    `- Free-form Comments: ${validatedInput.free_form_criterion_comments ? 'Enabled' : 'Disabled'}\n\n` +
                    `**Assignment Association:**\n` +
                    `- Assignment ID: ${validatedInput.assignment_id}\n` +
                    `- Used for Grading: ${validatedInput.use_for_grading ? 'Yes' : 'No'}\n` +
                    `- Association ID: ${association.id}\n\n` +
                    `The rubric is now available in SpeedGrader for this assignment.`
            }
          ]
        };

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        return {
          content: [
            {
              type: 'text' as const,
              text: `❌ Failed to create/attach rubric "${input.title}"\n\n` +
                    `**Error:** ${errorMessage}\n\n` +
                    `**Troubleshooting:**\n` +
                    `- Verify assignment ID ${input.assignment_id} exists in course ${input.course_id}\n` +
                    `- Ensure you have teacher/admin permissions for this course\n` +
                    `- Check that rubric criteria have valid point values\n` +
                    `- Verify each criterion has at least one rating`
            }
          ]
        };
      }
    }
  };
}
