import fs from 'fs';
import path from 'path';
import { CanvasClient } from '../canvas';
import { z } from 'zod';

const UploadFileInput = z.object({
  course_id: z.union([z.number().int(), z.string().regex(/^[0-9]+$/)]).transform(Number),
  filepath: z.string(),
  folder_id: z.number().int().optional(),
});

export const UploadFileInputSchema = {
  type: 'object' as const,
  properties: {
    course_id: { type: 'number', description: 'Canvas course ID' },
    filepath: { type: 'string', description: 'Path to local file to upload' },
    folder_id: { type: 'number', description: 'Optional Canvas folder ID' }
  },
  required: ['course_id','filepath']
};

export function uploadFileTool(client: CanvasClient) {
  return {
    name: 'upload_file',
    description: 'Upload a local file to a Canvas course Files area',
    inputSchema: UploadFileInputSchema,
    handler: async (rawInput: any) => {
      const input = UploadFileInput.parse(rawInput);
      const abs = path.isAbsolute(input.filepath) ? input.filepath : path.resolve(process.cwd(), input.filepath);
      if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
        return { content: [{ type: 'text' as const, text: `File not found: ${abs}` }] };
      }
      const filename = path.basename(abs);
      const size = fs.statSync(abs).size;

      // Step 1: start upload session
      const startResp = await fetch(`${client.getBaseUrl()}/api/v1/courses/${input.course_id}/files`, {
        method: 'POST',
        headers: client.authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ name: filename, size, parent_folder_id: input.folder_id, on_duplicate: 'rename' })
      });
      if (!startResp.ok) {
        const t = await startResp.text();
        throw new Error(`Upload init failed: ${startResp.status} ${t}`);
      }
      const startJson: any = await startResp.json();
      if (!startJson.upload_url) {
        throw new Error('Canvas did not return upload_url');
      }

      // Step 2: actual file upload (multipart form)
      const form = new FormData();
      Object.entries(startJson.upload_params || {}).forEach(([k,v]) => form.append(k, v as any));
      form.append('file', new Blob([fs.readFileSync(abs)]), filename);
      const uploadResp = await fetch(startJson.upload_url, { method: 'POST', body: form });
      if (!uploadResp.ok) {
        const t = await uploadResp.text();
        throw new Error(`File POST failed: ${uploadResp.status} ${t}`);
      }
      const uploadedMeta: any = await uploadResp.json();
      const fileId = uploadedMeta.id || uploadedMeta.attachment?.id;
      const url = uploadedMeta.url || uploadedMeta.attachment?.url;
      return { content: [{ type: 'text' as const, text: `Uploaded file #${fileId} ${filename}\nURL: ${url}` }] };
    }
  };
}
