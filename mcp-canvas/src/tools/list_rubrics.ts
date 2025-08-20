import { ListRubricsInput, ListRubricsInputSchema, ListRubricsInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function listRubricsTool(client: CanvasClient) {
  return {
    name: 'list_rubrics',
    description: 'List rubrics available in a course',
    inputSchema: ListRubricsInputSchema,
    handler: async (input: ListRubricsInputType) => {
      const v = ListRubricsInput.parse(input);
      const rubrics = await client.get<any[]>(`/api/v1/courses/${v.course_id}/rubrics`);
      const text = rubrics.map(r => `#${r.id} ${r.title} points:${r.points_possible}`).join('\n');
      return { content: [{ type: 'text' as const, text: text || 'No rubrics.' }] };
    }
  };
}
