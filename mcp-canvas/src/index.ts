// src/index.ts
import 'dotenv/config';
import fs from 'fs';
import path from 'path';
// Fallback: load parent workspace .env if vars still missing
if (!process.env.CANVAS_BASE_URL || !(process.env.CANVAS_TOKEN || process.env.CANVAS_API_TOKEN)) {
  try {
    const parentEnv = path.resolve(process.cwd(), '..', '.env');
    if (fs.existsSync(parentEnv)) {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const dotenv = require('dotenv');
      dotenv.config({ path: parentEnv });
    }
  } catch {/* ignore */}
}
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { CanvasClient } from './canvas';
import { createAssignmentTool } from './tools/create_assignment';
import { attachRubricTool } from './tools/attach_rubric';
import { listAssignmentsTool } from './tools/list_assignments';
import { createModuleTool } from './tools/create_module';
import { addModuleItemTool } from './tools/add_module_item';
import { createPageTool } from './tools/create_page';
import { listPagesTool } from './tools/list_pages';
import { createQuizTool } from './tools/create_quiz';
import { createQuizQuestionTool } from './tools/create_quiz_question';
import { createRubricTool } from './tools/create_rubric';
import { listRubricsTool } from './tools/list_rubrics';
import { uploadFileTool } from './tools/upload_file';

// Optional dynamically generated schemas (single source of truth from Python)
let generatedSchemas: any | null = null;
let generatedMeta: any | null = null;
try {
  const genPath = path.resolve(process.cwd(), 'generated_action_schemas.json');
  if (fs.existsSync(genPath)) {
    const raw = fs.readFileSync(genPath, 'utf-8');
    generatedSchemas = JSON.parse(raw);
    console.log('🧩 Loaded generated action schemas.');
  } else {
    // Try parent (if running from dist inside src relocation scenarios)
    const alt = path.resolve(process.cwd(), '..', 'generated_action_schemas.json');
    if (fs.existsSync(alt)) {
      const raw = fs.readFileSync(alt, 'utf-8');
      generatedSchemas = JSON.parse(raw);
      console.log('🧩 Loaded generated action schemas (parent).');
    }
  }
} catch (e) {
  console.warn('⚠️ Failed to load generated_action_schemas.json:', (e as Error).message);
}

// Load confirmation meta
try {
  const metaPath = path.resolve(process.cwd(), 'generated_action_meta.json');
  if (fs.existsSync(metaPath)) {
    generatedMeta = JSON.parse(fs.readFileSync(metaPath,'utf-8'));
    console.log('🛡️ Loaded action confirmation metadata.');
  } else {
    const alt = path.resolve(process.cwd(), '..', 'generated_action_meta.json');
    if (fs.existsSync(alt)) {
      generatedMeta = JSON.parse(fs.readFileSync(alt,'utf-8'));
      console.log('🛡️ Loaded action confirmation metadata (parent).');
    }
  }
} catch (e) {
  console.warn('⚠️ Failed to load generated_action_meta.json:', (e as Error).message);
}

// Mapping from tool name -> action metadata name (if different)
const ACTION_NAME_ALIASES: Record<string,string> = {
  'attach_rubric_to_assignment': 'attach_rubric'
};

// Global error visibility so VS Code surfaces issues instead of silent exits
process.on('unhandledRejection', (reason) => {
  console.error('[unhandledRejection]', reason);
});
process.on('uncaughtException', (err) => {
  console.error('[uncaughtException]', err);
});

// Validate environment variables
const baseUrl = process.env.CANVAS_BASE_URL;
const token = process.env.CANVAS_TOKEN || process.env.CANVAS_API_TOKEN;

if (!baseUrl || !token) {
  console.error('Error: Missing Canvas credentials.');
  console.error('Required: CANVAS_BASE_URL plus CANVAS_TOKEN (or CANVAS_API_TOKEN).');
  console.error('Populate either mcp-canvas/.env or root .env.');
  process.exit(1);
}

// Initialize Canvas client
const canvasClient = new CanvasClient(baseUrl, token);

// Defer connection test until after server is listening so MCP initialize can proceed
setImmediate(() => {
  console.log('🔌 Testing Canvas connection...');
  canvasClient.testConnection()
    .then(result => {
      if (result.success) {
        console.log(`✅ Connected to Canvas as: ${result.user?.name || 'Unknown User'}`);
      } else {
        console.warn(`⚠️ Canvas connection failed (continuing; tools will error): ${result.error}`);
      }
    })
    .catch(error => {
      console.warn(`⚠️ Canvas connection test exception (continuing): ${error.message}`);
    });
});

// Create MCP server
const server = new Server(
  {
    name: 'mcp-canvas',
    version: '0.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Register tools
const tools = [
  createAssignmentTool(canvasClient),
  attachRubricTool(canvasClient),
  listAssignmentsTool(canvasClient),
  createModuleTool(canvasClient),
  addModuleItemTool(canvasClient),
  createPageTool(canvasClient),
  listPagesTool(canvasClient),
  createQuizTool(canvasClient),
  createQuizQuestionTool(canvasClient),
  createRubricTool(canvasClient),
  listRubricsTool(canvasClient),
  uploadFileTool(canvasClient),
];

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: tools.map(tool => ({
      name: tool.name,
      description: (() => {
        let desc = tool.description;
        const actionName = ACTION_NAME_ALIASES[tool.name] || tool.name;
        if (generatedMeta?.actions?.[actionName]?.confirm) {
          desc += ' (CONFIRMATION REQUIRED)';
        }
        return desc;
      })(),
      inputSchema: (() => {
        if (generatedSchemas?.actions) {
          const actionName = ACTION_NAME_ALIASES[tool.name] || tool.name;
          const schema = generatedSchemas.actions[actionName];
            if (schema) {
              return schema;
            }
        }
        return tool.inputSchema; // fallback
      })(),
    })),
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  // Find the tool handler
  const tool = tools.find(t => t.name === name);
  if (!tool) {
    throw new Error(`Unknown tool: ${name}`);
  }

  try {
    // Execute the tool
    const result = await tool.handler(args as any);
    
    return result;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Tool execution failed: ${error.message}`);
    }
    throw new Error('Tool execution failed with unknown error');
  }
});

// Start the server
console.log('🚀 Starting MCP Canvas server...');
const transport = new StdioServerTransport();
server.connect(transport);

console.log('📡 MCP Canvas server is running and ready for connections');
console.log('Available tools:', tools.map(t => t.name).join(', '));

// Keep-alive (some hosts may terminate quiet processes); harmless no-op
setInterval(() => {}, 60_000).unref();

// Optional heartbeat for debugging (enable by setting DEBUG_MCP_CANVAS=1)
if (process.env.DEBUG_MCP_CANVAS) {
  setInterval(() => {
    console.log('[heartbeat] MCP Canvas server alive at', new Date().toISOString());
  }, 30_000).unref();
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down MCP Canvas server...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Shutting down MCP Canvas server...');
  process.exit(0);
});
