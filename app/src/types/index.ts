export type Role = 'user' | 'assistant' | 'system';

export interface Citation {
  id: string;
  title: string;
  url: string;
  snippet?: string;
}

export interface GeneratedImage {
  id: string;
  url: string;
  prompt?: string;
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  status: 'uploading' | 'processing' | 'ready' | 'error';
  progress?: number;
  url?: string;
  error?: string;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  model?: string;
  attachments?: Attachment[];
  citations?: Citation[];
  images?: GeneratedImage[];
  webSearch?: boolean;
  searchStatus?: string;
  isStreaming?: boolean;
  error?: string;
  editedFrom?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  model: string;
  messages: Message[];
  pinned?: boolean;
  archived?: boolean;
}

export type ProviderKind = 'local' | 'openai' | 'groq' | 'other';

export interface ModelInfo {
  id: string;
  name: string;
  provider: ProviderKind;
  group?: string;
  description?: string;
  contextLength?: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  avatarUrl?: string;
}

export interface ChatSendOptions {
  webSearch?: boolean;
  imageGeneration?: boolean;
  attachmentIds?: string[];
  maxTokens?: number;
}
