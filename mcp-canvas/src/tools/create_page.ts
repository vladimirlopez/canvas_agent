import { CreatePageInput, CreatePageInputSchema, CreatePageInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function createPageTool(client: CanvasClient) {
  return {
    name: 'create_page',
    description: 'Create a wiki page in a course',
    inputSchema: CreatePageInputSchema,
    handler: async (input: CreatePageInputType) => {
      const v = CreatePageInput.parse(input);
      const body = { wiki_page: { title: v.title, body: v.body || '', published: v.published } };
      const page = await client.post<any>(`/api/v1/courses/${v.course_id}/pages`, body);
      return { content: [{ type: 'text' as const, text: `Created page ${page.title}` }] };
    }
  };
}
