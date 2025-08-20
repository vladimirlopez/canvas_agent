import { AddModuleItemInput, AddModuleItemInputSchema, AddModuleItemInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function addModuleItemTool(client: CanvasClient) {
  return {
    name: 'add_module_item',
    description: 'Add an item (assignment/page/quiz/file) to a module',
    inputSchema: AddModuleItemInputSchema,
    handler: async (input: AddModuleItemInputType) => {
      const v = AddModuleItemInput.parse(input);
      const body: any = { module_item: { title: v.title, type: v.type } };
      if (v.content_id) body.module_item.content_id = v.content_id;
      const resp = await client.post<any>(`/api/v1/courses/${v.course_id}/modules/${v.module_id}/items`, body);
      return { content: [{ type: 'text' as const, text: `Added item ${resp.title} type=${resp.type} (#${resp.id})` }] };
    }
  };
}
