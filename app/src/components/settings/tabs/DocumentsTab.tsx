import { useState } from 'react';
import { SettingsSection, SettingsRow, Toggle, Select } from '../Shared';

export function DocumentsTab() {
  const [chunkSize, setChunkSize] = useState('1000');
  const [autoAttach, setAutoAttach] = useState(true);

  return (
    <div>
      <p className="mb-4 text-xs text-gray-400">
        Documents are uploaded through the composer's attach button, chunked, embedded, and retrieved via your
        backend's RAG pipeline (<code className="font-mono">POST /api/documents</code>). Only the most relevant
        excerpts are sent to the model, not the whole file.
      </p>
      <SettingsSection title="Retrieval (RAG)">
        <SettingsRow label="Chunk size" description="Passed to the backend document processor">
          <Select
            value={chunkSize}
            onChange={setChunkSize}
            options={[
              { value: '500', label: '500 tokens' },
              { value: '1000', label: '1000 tokens' },
              { value: '2000', label: '2000 tokens' }
            ]}
          />
        </SettingsRow>
        <SettingsRow label="Auto-attach to new messages" description="Keep uploaded documents in context for follow-ups">
          <Toggle checked={autoAttach} onChange={setAutoAttach} />
        </SettingsRow>
        <SettingsRow label="OCR for scanned PDFs" description="Not implemented on the backend yet — scanned/image-only PDFs will fail to upload">
          <Toggle checked={false} onChange={() => {}} />
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="Uploads">
        <SettingsRow label="Accepted file types" description="PDF, TXT, Markdown, DOCX">
          <span className="text-xs text-gray-400">.pdf .txt .md .docx</span>
        </SettingsRow>
        <SettingsRow label="Max file size" description="Enforced by your backend upload endpoint">
          <span className="text-xs text-gray-400">25 MB</span>
        </SettingsRow>
      </SettingsSection>
    </div>
  );
}
