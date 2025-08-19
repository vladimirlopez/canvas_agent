// src/tools/create_assignment.ts
import { CreateAssignmentInput, CreateAssignmentInputSchema, CreateAssignmentInputType, CanvasAssignment } from '../schemas';
import { CanvasClient } from '../canvas';

export function createAssignmentTool(client: CanvasClient) {
  return {
    name: 'create_assignment',
    description: 'Create a new assignment in a Canvas course with specified parameters',
    inputSchema: CreateAssignmentInputSchema,
    
    handler: async (input: CreateAssignmentInputType) => {
      try {
        // Validate input using Zod
        const validatedInput = CreateAssignmentInput.parse(input);
        
        // Prepare Canvas API payload
        const assignmentData = {
          assignment: {
            name: validatedInput.name,
            points_possible: validatedInput.points_possible,
            due_at: validatedInput.due_at,
            submission_types: validatedInput.submission_types,
            description: validatedInput.description_html || '',
            published: validatedInput.published,
          }
        };

        // Create assignment via Canvas API
        const result = await client.post<CanvasAssignment>(
          `/api/v1/courses/${validatedInput.course_id}/assignments`,
          assignmentData
        );

        return {
          content: [
            {
              type: 'text' as const,
              text: `✅ Successfully created assignment "${validatedInput.name}"\n\n` +
                    `**Assignment Details:**\n` +
                    `- ID: ${result.id}\n` +
                    `- Name: ${result.name}\n` +
                    `- Points: ${result.points_possible}\n` +
                    `- Due: ${result.due_at || 'Not set'}\n` +
                    `- Submission Types: ${result.submission_types?.join(', ')}\n` +
                    `- Published: ${result.published}\n` +
                    `- Canvas URL: ${result.html_url}\n\n` +
                    `The assignment is now available in your course.`
            }
          ]
        };

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        return {
          content: [
            {
              type: 'text' as const,
              text: `❌ Failed to create assignment "${input.name}"\n\n` +
                    `**Error:** ${errorMessage}\n\n` +
                    `**Troubleshooting:**\n` +
                    `- Verify course ID ${input.course_id} exists and you have teacher/admin access\n` +
                    `- Check that your Canvas API token has sufficient permissions\n` +
                    `- Ensure all required fields are properly formatted`
            }
          ]
        };
      }
    }
  };
}
