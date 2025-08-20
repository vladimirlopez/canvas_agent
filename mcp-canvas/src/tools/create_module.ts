import { CreateModuleInput, CreateModuleInputSchema, CreateModuleInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function createModuleTool(client: CanvasClient) {
  return {
    name: 'create_module',
    description: 'Create a module in a course',
    inputSchema: CreateModuleInputSchema,
    handler: async (input: CreateModuleInputType) => {
      const v = CreateModuleInput.parse(input);
      const body = { module: { name: v.name, published: v.published } };
      const mod = await client.post<any>(`/api/v1/courses/${v.course_id}/modules`, body);
      return { content: [{ type: 'text' as const, text: `Created module ${mod.name} (#${mod.id})` }] };
    }
  };
}
