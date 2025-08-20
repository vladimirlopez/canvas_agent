// src/schemas.ts
import { z } from 'zod';

// Common types
export const courseId = z.union([
  z.number().int().positive(), 
  z.string().regex(/^\d+$/)
]).transform(Number);

export const userId = courseId;

export const assignmentId = z.number().int().positive();

// Generic IDs
export const moduleId = z.number().int().positive();
export const quizId = z.number().int().positive();
export const pageTitle = z.string().min(1).max(255);

// Create Assignment Schema
export const CreateAssignmentInput = z.object({
  course_id: courseId,
  name: z.string().min(1).max(255),
  points_possible: z.number().min(0).default(100),
  due_at: z.string().datetime().optional(),
  submission_types: z.array(z.enum([
    'online_upload',
    'online_text_entry', 
    'external_tool',
    'none',
    'on_paper',
    'discussion_topic',
    'online_quiz',
    'media_recording'
  ])).min(1),
  description_html: z.string().optional(),
  published: z.boolean().default(true),
  grading_type: z.enum(['pass_fail', 'percent', 'letter_grade', 'gpa_scale', 'points']).default('points'),
  assignment_group_id: z.number().int().positive().optional(),
});

// MCP-compatible schema (JSON Schema format)
export const CreateAssignmentInputSchema = {
  type: "object" as const,
  properties: {
    course_id: { type: "number", description: "Canvas course ID" },
    name: { type: "string", description: "Assignment name" },
    points_possible: { type: "number", default: 100, description: "Maximum points" },
    due_at: { type: "string", format: "date-time", description: "Due date in ISO format" },
    submission_types: { 
      type: "array", 
      items: { 
        type: "string", 
        enum: ['online_upload', 'online_text_entry', 'external_tool', 'none']
      },
      description: "Allowed submission types"
    },
    description_html: { type: "string", description: "Assignment description (HTML)" },
    published: { type: "boolean", default: true, description: "Publish immediately" }
  },
  required: ["course_id", "name", "submission_types"]
};

// Rubric Schema
export const RubricCriterion = z.object({
  id: z.string().optional(),
  description: z.string().min(1),
  long_description: z.string().optional(),
  points: z.number().min(0),
  ratings: z.array(z.object({
    description: z.string().min(1),
    points: z.number().min(0),
    id: z.string().optional(),
  })).min(1),
});

export const AttachRubricInput = z.object({
  course_id: courseId,
  assignment_id: assignmentId,
  title: z.string().min(1).default('AI-Generated Rubric'),
  rubric: z.array(RubricCriterion).min(1),
  free_form_criterion_comments: z.boolean().default(false),
  use_for_grading: z.boolean().default(true),
});

export const AttachRubricInputSchema = {
  type: "object" as const,
  properties: {
    course_id: { type: "number", description: "Canvas course ID" },
    assignment_id: { type: "number", description: "Assignment ID to attach rubric to" },
    title: { type: "string", default: "AI-Generated Rubric", description: "Rubric title" },
    rubric: {
      type: "array",
      items: {
        type: "object",
        properties: {
          description: { type: "string", description: "Criterion description" },
          points: { type: "number", description: "Maximum points for this criterion" },
          ratings: {
            type: "array",
            items: {
              type: "object",
              properties: {
                description: { type: "string" },
                points: { type: "number" }
              }
            }
          }
        }
      }
    }
  },
  required: ["course_id", "assignment_id", "rubric"]
};

// List Assignments
export const ListAssignmentsInput = z.object({
  course_id: courseId,
});
export const ListAssignmentsInputSchema = {
  type: 'object' as const,
  properties: { course_id: { type: 'number', description: 'Canvas course ID' } },
  required: ['course_id']
};

// Modules
export const CreateModuleInput = z.object({
  course_id: courseId,
  name: z.string().min(1).max(255),
  published: z.boolean().default(true)
});
export const CreateModuleInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number', description: 'Canvas course ID' },
    name: { type: 'string', description: 'Module name' },
    published: { type: 'boolean', default: true }
  },
  required: ['course_id','name']
};

export const AddModuleItemInput = z.object({
  course_id: courseId,
  module_id: moduleId,
  type: z.enum(['Assignment','Page','File','ExternalUrl','ExternalTool','Quiz']).default('Assignment'),
  title: z.string().min(1),
  content_id: z.number().int().positive().optional()
});
export const AddModuleItemInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number' },
    module_id: { type: 'number' },
    type: { type: 'string', enum: ['Assignment','Page','File','ExternalUrl','ExternalTool','Quiz'] },
    title: { type: 'string' },
    content_id: { type: 'number' }
  },
  required: ['course_id','module_id','type','title']
};

// Pages
export const CreatePageInput = z.object({
  course_id: courseId,
  title: pageTitle,
  body: z.string().optional(),
  published: z.boolean().default(true)
});
export const CreatePageInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number' },
    title: { type: 'string' },
    body: { type: 'string' },
    published: { type: 'boolean', default: true }
  },
  required: ['course_id','title']
};

export const ListPagesInput = z.object({ course_id: courseId });
export const ListPagesInputSchema = {
  type: 'object' as const,
  properties: { course_id: { type: 'number' } },
  required: ['course_id']
};

// Quizzes
export const CreateQuizInput = z.object({
  course_id: courseId,
  name: z.string().min(1),
  description: z.string().optional(),
  due_at: z.string().datetime().optional(),
  shuffle_answers: z.boolean().default(true),
  published: z.boolean().default(true),
  time_limit: z.number().int().positive().optional(),
  question: z.string().optional(),
  answers: z.array(z.string()).optional()
});
export const CreateQuizInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number' },
    name: { type: 'string' },
    description: { type: 'string' },
    due_at: { type: 'string', format: 'date-time' },
    shuffle_answers: { type: 'boolean', default: true },
    published: { type: 'boolean', default: true },
    time_limit: { type: 'number', description: 'Minutes' },
    question: { type: 'string', description: 'If provided, creates first MC question.' },
    answers: { type: 'array', items: { type: 'string' }, description: 'MC answers (first is correct)' }
  },
  required: ['course_id','name']
};

export const CreateQuizQuestionInput = z.object({
  course_id: courseId,
  quiz_id: quizId,
  question: z.string().min(1),
  answers: z.array(z.string()).min(2)
});
export const CreateQuizQuestionInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number' },
    quiz_id: { type: 'number' },
    question: { type: 'string' },
    answers: { type: 'array', items: { type: 'string' } }
  },
  required: ['course_id','quiz_id','question','answers']
};

// Rubric list/create (separate from attach)
export const CreateRubricInput = z.object({
  course_id: courseId,
  title: z.string().min(1),
  criteria: z.array(z.object({
    description: z.string().min(1),
    points: z.number().min(0)
  })).min(1)
});
export const CreateRubricInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number' },
    title: { type: 'string' },
    criteria: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, points: { type: 'number' } } } }
  },
  required: ['course_id','title','criteria']
};

export const ListRubricsInput = z.object({ course_id: courseId });
export const ListRubricsInputSchema = {
  type: 'object' as const,
  properties: { course_id: { type: 'number' } },
  required: ['course_id']
};

// Canvas API response types
export interface CanvasAssignment {
  id: number;
  name: string;
  points_possible: number;
  due_at?: string;
  submission_types: string[];
  published: boolean;
  html_url: string;
}

export interface CanvasRubric {
  id: number;
  title: string;
  points_possible: number;
}

// Export types for TypeScript
export type CreateAssignmentInputType = z.infer<typeof CreateAssignmentInput>;
export type AttachRubricInputType = z.infer<typeof AttachRubricInput>;
export type ListAssignmentsInputType = z.infer<typeof ListAssignmentsInput>;
export type CreateModuleInputType = z.infer<typeof CreateModuleInput>;
export type AddModuleItemInputType = z.infer<typeof AddModuleItemInput>;
export type CreatePageInputType = z.infer<typeof CreatePageInput>;
export type ListPagesInputType = z.infer<typeof ListPagesInput>;
export type CreateQuizInputType = z.infer<typeof CreateQuizInput>;
export type CreateQuizQuestionInputType = z.infer<typeof CreateQuizQuestionInput>;
export type CreateRubricInputType = z.infer<typeof CreateRubricInput>;
export type ListRubricsInputType = z.infer<typeof ListRubricsInput>;
