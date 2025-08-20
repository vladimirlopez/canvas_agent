import { ListAssignmentsInput, ListAssignmentsInputSchema, ListAssignmentsInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function listAssignmentsTool(client: CanvasClient) {
  return {
    name: 'list_assignments',
    description: 'List assignments for a course',
    inputSchema: ListAssignmentsInputSchema,
    handler: async (input: ListAssignmentsInputType) => {
      const validated = ListAssignmentsInput.parse(input);
      const assignments = await client.get<any[]>(`/api/v1/courses/${validated.course_id}/assignments`);
      const summary = assignments.map(a => `#${a.id} ${a.name} (points: ${a.points_possible ?? 'n/a'}) due: ${a.due_at ?? '—'}`).join('\n');
      return { content: [{ type: 'text' as const, text: summary || 'No assignments.' }] };
    }
  };
}
