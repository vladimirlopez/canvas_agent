// src/schemas.ts
import { z } from 'zod';

// Common types
export const courseId = z.union([
  z.number().int().positive(), 
  z.string().regex(/^\d+$/)
]).transform(Number);

export const userId = courseId;

export const assignmentId = z.number().int().positive();

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
