# MCP Canvas Server

A Model Context Protocol (MCP) server for Canvas LMS automation, enabling natural language control of Canvas through various LLM clients.

## 🚀 Features

- **Create assignments** with natural language descriptions
- **Attach rubrics** to assignments for structured grading
- **Canvas API integration** with automatic retries and rate limiting
- **Multiple client support** - VS Code Copilot, Gemini CLI, Claude Desktop

## 🛠️ Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Canvas credentials
   ```

3. **Build the server:**
   ```bash
   npm run build
   ```

4. **Test the server:**
   ```bash
   npm run dev
   ```

## 🔧 VS Code Integration

1. Ensure `.vscode/mcp.json` exists in your workspace
2. Set the `CANVAS_TOKEN` environment variable
3. Open VS Code Copilot Chat
4. Enable Agent Mode → Tools → Canvas

## 📝 Example Usage

**Create an assignment:**
```
Create an assignment "Essay 1" worth 50 points in course 12625554, allowing online_upload and online_text_entry, due next Friday at 11:59 PM
```

**Attach a rubric:**
```
Attach a rubric to assignment 123 in course 12625554 with criteria for thesis (5 points), analysis (10 points), and writing (5 points)
```

## 🏗️ Available Tools

- `create_assignment` - Create assignments in Canvas courses
- `attach_rubric_to_assignment` - Create and attach rubrics to assignments

## 🔍 Testing

Your Canvas credentials from the main project are automatically used. The server tests the connection on startup.

## 📚 Canvas API

This server uses the Canvas REST API with your personal access token. Ensure you have teacher or admin permissions for the courses you want to modify.
