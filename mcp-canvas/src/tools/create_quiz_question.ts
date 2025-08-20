import { CreateQuizQuestionInput, CreateQuizQuestionInputSchema, CreateQuizQuestionInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function createQuizQuestionTool(client: CanvasClient) {
  return {
    name: 'create_quiz_question',
    description: 'Add a multiple choice question to an existing quiz',
    inputSchema: CreateQuizQuestionInputSchema,
    handler: async (input: CreateQuizQuestionInputType) => {
      const v = CreateQuizQuestionInput.parse(input);
      const answers = v.answers.map((a, i) => ({ answer_text: a, answer_weight: i === 0 ? 100 : 0 }));
      const body = { question: { question_name: v.question.slice(0, 60), question_text: v.question, question_type: 'multiple_choice_question', points_possible: 1, answers } };
      const q = await client.post<any>(`/api/v1/courses/${v.course_id}/quizzes/${v.quiz_id}/questions`, body);
      return { content: [{ type: 'text' as const, text: `Added question #${q.id} to quiz ${v.quiz_id}` }] };
    }
  };
}
