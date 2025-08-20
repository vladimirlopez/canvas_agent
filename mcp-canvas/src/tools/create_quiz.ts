import { CreateQuizInput, CreateQuizInputSchema, CreateQuizInputType } from '../schemas';
import { CanvasClient } from '../canvas';

export function createQuizTool(client: CanvasClient) {
  return {
    name: 'create_quiz',
    description: 'Create a real (classic) quiz; optional first MC question',
    inputSchema: CreateQuizInputSchema,
    handler: async (input: CreateQuizInputType) => {
      const v = CreateQuizInput.parse(input);
      const quizBody = { quiz: { title: v.name, description: v.description || '', due_at: v.due_at, shuffle_answers: v.shuffle_answers, published: v.published, time_limit: v.time_limit } };
      const quiz = await client.post<any>(`/api/v1/courses/${v.course_id}/quizzes`, quizBody);
      let extra = '';
      if (v.question && v.answers && v.answers.length >= 2) {
        const answers = v.answers.map((a, i) => ({ answer_text: a, answer_weight: i === 0 ? 100 : 0 }));
        const qBody = { question: { question_name: v.question.slice(0, 60), question_text: v.question, question_type: 'multiple_choice_question', points_possible: 1, answers } };
        await client.post<any>(`/api/v1/courses/${v.course_id}/quizzes/${quiz.id}/questions`, qBody);
        extra = '\nAdded first question.';
      }
      return { content: [{ type: 'text' as const, text: `Created quiz ${quiz.title} (#${quiz.id}).${extra}` }] };
    }
  };
}
