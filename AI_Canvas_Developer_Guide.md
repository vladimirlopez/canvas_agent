
# AI + Canvas LMS Automation — Developer Guide (MCP + API)

> **Goal**: Enable natural‑language control of Canvas LMS (create courses/assignments, build rubrics, write comments, upload files, analyze performance) using an **MCP server** that exposes focused tools to LLM clients (VS Code Agent Mode/Copilot Chat, Gemini CLI, Claude Desktop, Cursor), with a safe fallback to direct Canvas REST API scripts for batch jobs.

---

## TL;DR (What to build)

- A **Node/TypeScript MCP server** (`mcp-canvas`) that wraps the Canvas REST API as a handful of **safe, purpose‑built tools** (e.g., `create_assignment`, `attach_rubric`, `comment_and_grade`, `upload_file_to_course`, `copy_course_content`).  
- Optional **Python utilities** (using `canvasapi`) for bulk operations and analytics jobs that you can call from the MCP server or run standalone.  
- Clients:
  - **VS Code Agent Mode** to invoke tools via Copilot Chat inside your editor.
  - **Gemini CLI** to drive the same tools from your terminal.
  - (Optional) **Claude Desktop / Cursor**, which also support MCP.

**Why MCP?** It gives the LLM structured, least‑privilege actions and typed input schemas (zod), rather than free‑form HTTP. If a user asks for something not implemented, the server can decline with guidance or you can provide a guarded `canvas_raw` tool for advanced use.

---

## 1) Requirements & Accounts

- **Canvas environment**
  - For quick testing, a **Canvas Free‑for‑Teacher (FFT)** account works, but note:
    - You usually cannot create Developer Keys or install LTI apps. Use **personal access tokens** and operate **only within your courses**.
    - Some admin‑level endpoints (e.g., creating courses at the account level) are not available to non‑admins.
  - For production or broader automation, request an **institutional sandbox** with:
    - **Admin** or elevated permissions for account‑level operations.
    - **Developer Key** if you plan to build an LTI app or use OAuth beyond personal tokens.

- **Local setup**
  - Node.js 20+, pnpm/npm
  - Python 3.11+ (optional utilities)
  - VS Code (latest) or another MCP client (Gemini CLI, Claude Desktop, Cursor)

- **Secrets**
  - `CANVAS_BASE_URL` (e.g., `https://<your-domain>.instructure.com`)
  - `CANVAS_TOKEN` (personal access token from **Account → Settings → New Access Token**)

---

## 2) Architecture Overview

```
+----------------------+        MCP tools        +-----------------------+
|  LLM Client          |  ───────────────────▶   |  MCP Server (Node)    |
|  (VS Code Agent,     |    create_assignment    |  - Validates inputs   |
|   Gemini CLI, etc.)  |    attach_rubric        |  - Calls Canvas REST  |
|                      |    comment_and_grade    |  - Logs, throttles    |
|  ◀────────────────── |    upload_file          |                       |
|  Tool results        |    copy_course_content  |                       |
+----------------------+                          +-----------┬-----------+
                                                         REST  │
                                                              ▼
                                                      +---------------+
                                                      |  Canvas REST  |
                                                      +---------------+
```

Keep two paths:
- **Agent path (MCP + LLM)** for ad‑hoc, natural‑language tasks.
- **Script path (direct API)** for scheduled/batch jobs and analytics.

---

## 3) Project Layout

```
ai-canvas/
├─ mcp-canvas/                # TypeScript MCP server
│  ├─ src/
│  │  ├─ index.ts             # server bootstrap
│  │  ├─ canvas.ts            # minimal Canvas REST client (fetch + retry)
│  │  ├─ tools/
│  │  │  ├─ create_assignment.ts
│  │  │  ├─ attach_rubric.ts
│  │  │  ├─ comment_and_grade.ts
│  │  │  ├─ upload_file_to_course.ts
│  │  │  └─ copy_course_content.ts
│  │  └─ schemas.ts           # zod input schemas/types
│  ├─ package.json
│  ├─ .env.example
│  └─ README.md
└─ scripts/                   # optional Python batch/analytics
   ├─ bulk_create_assignments.py
   ├─ export_grades_csv.py
   └─ README.md
```

---

## 4) TypeScript MCP Server — Skeleton

### Install

```bash
mkdir -p ai-canvas/mcp-canvas && cd $_
npm init -y
npm i @modelcontextprotocol/sdk zod undici dotenv
npm i -D typescript ts-node @types/node
npx tsc --init
```

### `src/canvas.ts` — tiny Canvas REST client with retry

```ts
// src/canvas.ts
import { setTimeout as wait } from 'node:timers/promises';
import { fetch } from 'undici';

export class CanvasClient {
  constructor(private baseUrl: string, private token: string) {}

  private headers(extra: Record<string, string> = {}) {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Accept': 'application/json',
      ...extra,
    };
  }

  async request<T>(method: string, path: string, body?: any, contentType = 'application/json'): Promise<T> {
    const url = new URL(path, this.baseUrl).toString();
    const options: any = { method, headers: this.headers() };
    if (body) {
      if (contentType === 'application/json') {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
      } else {
        // multipart handled by caller
        options.body = body;
      }
    }

    for (let attempt = 0; attempt < 5; attempt++) {
      const res = await fetch(url, options);
      if (res.status === 429) {
        const retryAfter = Number(res.headers.get('Retry-After') ?? '1');
        await wait((retryAfter + attempt) * 1000);
        continue;
      }
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`Canvas ${method} ${path} failed ${res.status} ${res.statusText}: ${text}`);
      }
      return (await res.json()) as T;
    }
    throw new Error(`Canvas ${method} ${path} failed after retries`);
  }

  get<T>(path: string) { return this.request<T>('GET', path); }
  post<T>(path: string, body?: any) { return this.request<T>('POST', path, body); }
  put<T>(path: string, body?: any) { return this.request<T>('PUT', path, body); }
  delete<T>(path: string) { return this.request<T>('DELETE', path); }
}
```

### `src/schemas.ts` — input validation

```ts
// src/schemas.ts
import { z } from 'zod';

export const courseId = z.union([z.number().int().positive(), z.string().regex(/^\d+$/)]).transform(Number);
export const userId   = courseId;

export const CreateAssignmentInput = z.object({
  course_id: courseId,
  name: z.string().min(1),
  points_possible: z.number().min(0).default(100),
  due_at: z.string().datetime().optional(),
  submission_types: z.array(z.enum(['online_upload','online_text_entry','external_tool','none'])).min(1),
  description_html: z.string().optional(),
});

export const AttachRubricInput = z.object({
  course_id: courseId,
  assignment_id: z.number().int().positive(),
  rubric: z.array(z.object({
    description: z.string(),
    long_description: z.string().optional(),
    points: z.number().min(0),
    ratings: z.array(z.object({ description: z.string(), points: z.number().min(0) })).min(1),
    id: z.string().optional(), // criterion_id
  })).min(1),
  free_form_criterion_comments: z.boolean().default(false),
});

export const CommentAndGradeInput = z.object({
  course_id: courseId,
  assignment_id: z.number().int().positive(),
  user_id: userId,
  posted_grade: z.union([z.string(), z.number()]).optional(),
  text_comment: z.string().optional(),
  rubric_assessment: z.record(z.string(), z.object({
    points: z.number().optional(),
    rating_id: z.string().optional(),
    comments: z.string().optional(),
  })).optional()
});

export const UploadFileInput = z.object({
  course_id: courseId,
  filename: z.string(),
  mime_type: z.string().default('application/octet-stream'),
  folder_id: z.number().int().optional(), // optional target folder
  file_bytes_b64: z.string().describe('Base64-encoded file payload'),
});

export const CopyCourseContentInput = z.object({
  source_course_id: courseId,
  dest_course_id: courseId,
  copy_everything: z.boolean().default(true)
});
```

### Tools

#### `src/tools/create_assignment.ts`
```ts
import { z } from 'zod';
import { CreateAssignmentInput } from '../schemas';
import { CanvasClient } from '../canvas';

export default function createAssignmentTool(client: CanvasClient) {
  return {
    name: 'create_assignment',
    description: 'Create an assignment in a course',
    inputSchema: CreateAssignmentInput,
    handler: async (input: z.infer<typeof CreateAssignmentInput>) => {
      const payload = {
        assignment: {
          name: input.name,
          points_possible: input.points_possible,
          due_at: input.due_at,
          submission_types: input.submission_types,
          description: input.description_html,
          published: true
        }
      };
      const data = await client.post(`/api/v1/courses/${input.course_id}/assignments`, payload);
      return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
    }
  };
}
```

#### `src/tools/attach_rubric.ts`
```ts
import { z } from 'zod';
import { AttachRubricInput } from '../schemas';
import { CanvasClient } from '../canvas';

export default function attachRubricTool(client: CanvasClient) {
  return {
    name: 'attach_rubric_to_assignment',
    description: 'Create a rubric in a course and associate it with an assignment',
    inputSchema: AttachRubricInput,
    handler: async (input: z.infer<typeof AttachRubricInput>) => {
      // Create rubric
      const rubricBody = {
        rubric: input.rubric.map((c, idx) => ({
          points: c.points,
          description: c.description,
          long_description: c.long_description ?? '',
          id: c.id ?? `crit_${idx}`,
          ratings: c.ratings
        })),
        title: 'AI‑Generated Rubric',
        points_possible: input.rubric.reduce((a, c) => a + c.points, 0),
        free_form_criterion_comments: input.free_form_criterion_comments
      };
      const rubric = await client.post(
        `/api/v1/courses/${input.course_id}/rubrics`,
        rubricBody
      );

      // Associate rubric with assignment
      const assoc = await client.post(
        `/api/v1/courses/${input.course_id}/rubric_associations`,
        {
          rubric_association: {
            association_type: 'Assignment',
            association_id: input.assignment_id,
            rubric_id: rubric.id,
            use_for_grading: true
          }
        }
      );

      return { content: [{ type: 'text', text: JSON.stringify({ rubric, assoc }, null, 2) }] };
    }
  };
}
```

#### `src/tools/comment_and_grade.ts`
```ts
import { z } from 'zod';
import { CommentAndGradeInput } from '../schemas';
import { CanvasClient } from '../canvas';

export default function commentAndGradeTool(client: CanvasClient) {
  return {
    name: 'comment_and_grade_submission',
    description: 'Post a text comment and/or grade on a student submission',
    inputSchema: CommentAndGradeInput,
    handler: async (input: z.infer<typeof CommentAndGradeInput>) => {
      const body: any = {};
      if (input.posted_grade !== undefined) body['submission[posted_grade]'] = String(input.posted_grade);
      if (input.text_comment) body['comment[text_comment]'] = input.text_comment;
      if (input.rubric_assessment) {
        for (const [crit, val] of Object.entries(input.rubric_assessment)) {
          if (val.points !== undefined) body[`rubric_assessment[${crit}][points]`] = val.points;
          if (val.rating_id !== undefined) body[`rubric_assessment[${crit}][rating_id]`] = val.rating_id;
          if (val.comments) body[`rubric_assessment[${crit}][comments]`] = val.comments;
        }
      }
      const data = await client.put(
        `/api/v1/courses/${input.course_id}/assignments/${input.assignment_id}/submissions/${input.user_id}`,
        body
      );
      return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
    }
  };
}
```

#### `src/tools/upload_file_to_course.ts` (3‑step upload)
```ts
import { z } from 'zod';
import { UploadFileInput } from '../schemas';
import { CanvasClient } from '../canvas';
import { fetch, FormData, File } from 'undici';

export default function uploadFileToCourseTool(client: CanvasClient) {
  return {
    name: 'upload_file_to_course',
    description: 'Upload a file into a course Files area',
    inputSchema: UploadFileInput,
    handler: async (input: z.infer<typeof UploadFileInput>) => {
      // Step 1: Start upload
      const start = await client.post(
        `/api/v1/courses/${input.course_id}/files`,
        {
          name: input.filename,
          size: Math.ceil(Buffer.from(input.file_bytes_b64, 'base64').length),
          content_type: input.mime_type,
          parent_folder_id: input.folder_id
        }
      );

      // Step 2: Upload to provided URL
      const fd = new FormData();
      for (const [k, v] of Object.entries(start.upload_params)) fd.set(k, String(v));
      const bytes = Buffer.from(input.file_bytes_b64, 'base64');
      fd.set('file', new File([bytes], input.filename, { type: input.mime_type }));
      const uploadRes = await fetch(start.upload_url, { method: 'POST', body: fd });
      if (!uploadRes.ok) throw new Error(`S3 upload failed: ${uploadRes.status} ${uploadRes.statusText}`);
      const json = await uploadRes.json();

      // Step 3: Canvas confirms and returns file object
      return { content: [{ type: 'text', text: JSON.stringify(json, null, 2) }] };
    }
  };
}
```

#### `src/tools/copy_course_content.ts` (Content Migrations API)
```ts
import { z } from 'zod';
import { CopyCourseContentInput } from '../schemas';
import { CanvasClient } from '../canvas';

export default function copyCourseContentTool(client: CanvasClient) {
  return {
    name: 'copy_course_content',
    description: 'Copy content from one course into another (Content Migrations API)',
    inputSchema: CopyCourseContentInput,
    handler: async (input: z.infer<typeof CopyCourseContentInput>) => {
      const payload = {
        migration_type: 'course_copy_importer',
        settings: { source_course_id: input.source_course_id },
      };
      const migration = await client.post(
        `/api/v1/courses/${input.dest_course_id}/content_migrations`,
        payload
      );
      return { content: [{ type: 'text', text: JSON.stringify(migration, null, 2) }] };
    }
  };
}
```

### `src/index.ts` — register tools + start MCP (stdio)
```ts
import 'dotenv/config';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CanvasClient } from './canvas';
import createAssignmentTool from './tools/create_assignment';
import attachRubricTool from './tools/attach_rubric';
import commentAndGradeTool from './tools/comment_and_grade';
import uploadFileToCourseTool from './tools/upload_file_to_course';
import copyCourseContentTool from './tools/copy_course_content';

const server = new McpServer({ name: 'mcp-canvas', version: '0.1.0' });

const base = process.env.CANVAS_BASE_URL!;
const token = process.env.CANVAS_TOKEN!;
if (!base || !token) throw new Error('Set CANVAS_BASE_URL and CANVAS_TOKEN');

const client = new CanvasClient(base, token);

// Register tools
server.addTool(createAssignmentTool(client));
server.addTool(attachRubricTool(client));
server.addTool(commentAndGradeTool(client));
server.addTool(uploadFileToCourseTool(client));
server.addTool(copyCourseContentTool(client));

// Optional: add a guarded raw endpoint for advanced users
// server.addTool(canvasRawTool(client)).disable();

const transport = new StdioServerTransport();
server.connect(transport);
```

### Run
```bash
# in ai-canvas/mcp-canvas
echo "CANVAS_BASE_URL=https://<your>.instructure.com" > .env
echo "CANVAS_TOKEN=<your PAT>" >> .env
npx ts-node src/index.ts
```

---

## 5) Wire It Into Clients

### A) VS Code (Copilot Chat) — Agent Mode + MCP

1) Add `.vscode/mcp.json` to your workspace:
```jsonc
{
  "servers": {
    "Canvas": {
      "type": "stdio",
      "command": "node",
      "args": ["dist/index.js"], // or use ts-node in dev
      "env": {
        "CANVAS_BASE_URL": "https://<your>.instructure.com",
        "CANVAS_TOKEN": "${env:CANVAS_TOKEN}"
      }
    }
  }
}
```
2) Open **Chat** → select **Agent mode** → **Tools** → enable *Canvas*.  
3) Example prompt: “Create an assignment ‘Essay 1’ worth 50 points in course 12345, `online_upload`, due next Friday 11:59pm.”

### B) Gemini CLI

Configure a local MCP server entry in your CLI settings (paths vary by OS):
```jsonc
{
  "mcpServers": {
    "Canvas": {
      "type": "stdio",
      "command": "node",
      "args": ["/absolute/path/to/ai-canvas/mcp-canvas/dist/index.js"],
      "env": {
        "CANVAS_BASE_URL": "https://<your>.instructure.com",
        "CANVAS_TOKEN": "env:CANVAS_TOKEN"
      }
    }
  }
}
```
Then run `gemini`, and call tools with `@Canvas ...` or browse them with your CLI’s MCP commands.

### C) (Optional) Claude Desktop / Cursor

Both can act as MCP clients; configure the server similarly via stdio or their MCP settings UI.

---

## 6) Python Helpers (Optional)

Install:
```bash
python -m venv .venv && source .venv/bin/activate
pip install canvasapi python-dotenv pandas
```

**`scripts/bulk_create_assignments.py`**
```python
from canvasapi import Canvas
from dotenv import load_dotenv
import os, csv

load_dotenv()
canvas = Canvas(os.environ["CANVAS_BASE_URL"], os.environ["CANVAS_TOKEN"])

COURSE_ID = int(os.environ["COURSE_ID"])
course = canvas.get_course(COURSE_ID)

with open('assignments.csv') as f:
    for row in csv.DictReader(f):
        course.create_assignment({
            "name": row["name"],
            "points_possible": float(row.get("points", 100)),
            "due_at": row.get("due_at"),  # ISO8601
            "submission_types": row.get("submission_types","online_upload").split("|"),
            "published": True
        })
print("Done.")
```

**`scripts/export_grades_csv.py`**
```python
from canvasapi import Canvas
from dotenv import load_dotenv
import os, csv

load_dotenv()
canvas = Canvas(os.environ["CANVAS_BASE_URL"], os.environ["CANVAS_TOKEN"])
course = canvas.get_course(int(os.environ["COURSE_ID"]))

students = list(course.get_users(enrollment_type=['student']))
assignments = list(course.get_assignments())

with open('grades_export.csv','w',newline='') as f:
    w = csv.writer(f)
    w.writerow(['student_id','student_name']+[a.name for a in assignments])
    for s in students:
        row=[s.id, s.name]
        for a in assignments:
            try:
                sub = a.get_submission(s.id)
                row.append(sub.score if sub and sub.score is not None else "")
            except Exception:
                row.append("")
        w.writerow(row)

print("grades_export.csv written")
```

**Example `assignments.csv`**
```csv
name,points,submission_types,due_at
Homework 1,100,online_upload,2025-09-05T23:59:00Z
Lab Report 1,50,online_upload|online_text_entry,2025-09-12T23:59:00Z
Essay 1,50,online_text_entry,2025-09-19T23:59:00Z
```

---

## 7) Safety, Scopes, and Guardrails

- **Least privilege**: Use personal tokens scoped to your courses for dev; request admin keys only when needed.
- **Dangerous actions**: Avoid implementing deletes or enrollments in early versions.
- **Throttling**: Handle HTTP 429 with backoff; monitor rate‑limit headers.
- **Input validation**: zod schemas prevent malformed tool calls.
- **PII/FERPA**: Don’t log submissions/grades in plaintext; redact identifiers in errors.
- **Audit**: Log who/what/when/payload (without sensitive bodies).

---

## 8) FFT vs Admin Capabilities

- **FFT**: Great for prototyping assignments, rubrics, files, grading **inside a course you own**.  
- **Admin‑only**: Creating courses via API (`POST /accounts/:id/courses`), Developer Keys/LTI app installs, large quotas and org‑wide analytics.
- **Workarounds**: Manually create a sandbox course in the UI; then automate everything **within** that course via API/MCP tools.

---

## 9) Analytics Options

- **Canvas Data 2 / DAP** (institutional): Query near‑real‑time datasets in your data warehouse (e.g., BigQuery). Best for dashboards and longitudinal analysis.  
- **REST + Pandas** (no DAP): Use the `scripts/export_grades_csv.py` path, then analyze with Python locally.

---

## 10) Minimal Test Plan

1. **Create assignment** → verify in Canvas UI.  
2. **Attach rubric** → verify in SpeedGrader.  
3. **Upload file** → verify in Files.  
4. **Comment & grade** → verify in Gradebook.  
5. **Copy course content** → verify modules/pages appear in destination.

Add unit tests with HTTP mocks (e.g., `msw`/`nock`) and a simple live smoke test suite targeting a disposable sandbox course.

---

## 11) Troubleshooting

- **401/403**: Check token, course role/permissions, and resource IDs. Admin‑level endpoints won’t work without admin rights.  
- **429**: You’re throttled; retry with exponential backoff and respect `Retry‑After`.  
- **Rubric association fails**: Ensure rubric exists in the **same course** and association type is **Assignment**.  
- **FFT can’t create courses via API**: Create course in UI or move to an admin sandbox.

---

## 12) Roadmap (Nice‑to‑have Tools)

- `create_module`, `create_page`, `publish_course_items`  
- `list_missing_submissions`, `message_students_who`  
- `report_course_health` (wrap a Python analysis as an MCP tool)  
- Admin‑profile tools: `create_course`, `enroll_user`, guarded `canvas_raw`

---

## 13) Appendix

### A) Example Rubric JSON (criteria array)
```json
[
  {
    "id": "thesis",
    "description": "Thesis / Problem Statement",
    "long_description": "Clear, testable, relevant",
    "points": 5,
    "ratings": [
      { "description": "Exemplary", "points": 5 },
      { "description": "Proficient", "points": 4 },
      { "description": "Developing", "points": 3 },
      { "description": "Beginning", "points": 1 }
    ]
  },
  {
    "id": "analysis",
    "description": "Analysis & Reasoning",
    "points": 10,
    "ratings": [
      { "description": "Exemplary", "points": 10 },
      { "description": "Proficient", "points": 8 },
      { "description": "Developing", "points": 6 },
      { "description": "Beginning", "points": 3 }
    ]
  },
  {
    "id": "mechanics",
    "description": "Writing Mechanics",
    "points": 5,
    "ratings": [
      { "description": "Clean", "points": 5 },
      { "description": "Minor issues", "points": 4 },
      { "description": "Several issues", "points": 3 },
      { "description": "Major issues", "points": 1 }
    ]
  }
]
```

### B) Example `.env`
```ini
CANVAS_BASE_URL=https://<your>.instructure.com
CANVAS_TOKEN=<your personal access token>
COURSE_ID=12345
```

### C) Example `.vscode/mcp.json`
```jsonc
{
  "servers": {
    "Canvas": {
      "type": "stdio",
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "CANVAS_BASE_URL": "https://<your>.instructure.com",
        "CANVAS_TOKEN": "${env:CANVAS_TOKEN}"
      }
    }
  }
}
```

---

**Happy building!**
