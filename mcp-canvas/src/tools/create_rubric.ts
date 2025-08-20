import { CreateRubricInput, CreateRubricInputSchema, CreateRubricInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function createRubricTool(client: CanvasClient) {
  return {
    name: 'create_rubric',
    description: 'Create a rubric (no immediate attachment)',
    inputSchema: CreateRubricInputSchema,
    handler: async (input: CreateRubricInputType) => {
      const v = CreateRubricInput.parse(input);
      const rubric = await client.post<any>(`/api/v1/courses/${v.course_id}/rubrics`, {
        title: v.title,
        rubric: v.criteria.map((c, i) => ({ id: `crit_${i}`, description: c.description, points: c.points, ratings: [ { id: `r_${i}_full`, description: 'Full Credit', points: c.points }, { id: `r_${i}_zero`, description: 'No Credit', points: 0 } ] })),
        points_possible: v.criteria.reduce((t,c)=>t+c.points,0)
      });
      return { content: [{ type: 'text' as const, text: `Created rubric ${rubric.title} (#${rubric.id})` }] };
    }
  };
}
