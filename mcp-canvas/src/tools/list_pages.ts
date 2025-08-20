import { ListPagesInput, ListPagesInputSchema, ListPagesInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function listPagesTool(client: CanvasClient) {
  return {
    name: 'list_pages',
    description: 'List wiki pages for a course',
    inputSchema: ListPagesInputSchema,
    handler: async (input: ListPagesInputType) => {
      const v = ListPagesInput.parse(input);
      const pages = await client.get<any[]>(`/api/v1/courses/${v.course_id}/pages`);
      const text = pages.map(p => `${p.title} (url: ${p.url})`).join('\n');
      return { content: [{ type: 'text' as const, text: text || 'No pages.' }] };
    }
  };
}
