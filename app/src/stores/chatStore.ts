import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Attachment, ChatSendOptions, Conversation, Message } from '@/types';
import { streamChat } from '@/services/api';

interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  streamingId: string | null;
  abortController: AbortController | null;

  newConversation: (model: string) => string;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  togglePin: (id: string) => void;
  clearAll: () => void;

  sendMessage: (content: string, model: string, options?: ChatSendOptions, attachments?: Attachment[]) => void;
  editMessage: (messageId: string, newContent: string, model: string) => void;
  regenerate: (messageId: string, model: string) => void;
  stopGenerating: () => void;
}

function makeConversation(model: string): Conversation {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: 'New Chat',
    createdAt: now,
    updatedAt: now,
    model,
    messages: []
  };
}

function titleFromContent(content: string): string {
  const clean = content.trim().replace(/\s+/g, ' ');
  return clean.length > 48 ? clean.slice(0, 48) + '…' : clean || 'New Chat';
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeId: null,
      streamingId: null,
      abortController: null,

      newConversation: (model) => {
        const convo = makeConversation(model);
        set((s) => ({ conversations: [convo, ...s.conversations], activeId: convo.id }));
        return convo.id;
      },

      selectConversation: (id) => set({ activeId: id }),

      deleteConversation: (id) => {
        set((s) => {
          const remaining = s.conversations.filter((c) => c.id !== id);
          const activeId = s.activeId === id ? remaining[0]?.id ?? null : s.activeId;
          return { conversations: remaining, activeId };
        });
      },

      renameConversation: (id, title) => {
        set((s) => ({
          conversations: s.conversations.map((c) => (c.id === id ? { ...c, title, updatedAt: Date.now() } : c))
        }));
      },

      togglePin: (id) => {
        set((s) => ({
          conversations: s.conversations.map((c) => (c.id === id ? { ...c, pinned: !c.pinned } : c))
        }));
      },

      clearAll: () => set({ conversations: [], activeId: null }),

      sendMessage: (content, model, options, attachments) => {
        let { activeId } = get();
        if (!activeId || !get().conversations.find((c) => c.id === activeId)) {
          activeId = get().newConversation(model);
        }
        const userMsg: Message = {
          id: crypto.randomUUID(),
          role: 'user',
          content,
          createdAt: Date.now(),
          attachments,
          webSearch: options?.webSearch
        };
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          createdAt: Date.now(),
          model,
          isStreaming: true
        };

        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== activeId) return c;
            const isFirst = c.messages.length === 0;
            return {
              ...c,
              title: isFirst ? titleFromContent(content) : c.title,
              model,
              updatedAt: Date.now(),
              messages: [...c.messages, userMsg, assistantMsg]
            };
          })
        }));

        runStream(activeId!, assistantMsg.id, model, options, set, get);
      },

      editMessage: (messageId, newContent, model) => {
        const { activeId, conversations } = get();
        const convo = conversations.find((c) => c.id === activeId);
        if (!convo) return;
        const idx = convo.messages.findIndex((m) => m.id === messageId);
        if (idx === -1) return;

        const truncated = convo.messages.slice(0, idx);
        const editedUser: Message = { ...convo.messages[idx], content: newContent, createdAt: Date.now() };
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          createdAt: Date.now(),
          model,
          isStreaming: true
        };

        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === activeId
              ? { ...c, messages: [...truncated, editedUser, assistantMsg], updatedAt: Date.now() }
              : c
          )
        }));

        runStream(activeId!, assistantMsg.id, model, undefined, set, get);
      },

      regenerate: (messageId, model) => {
        const { activeId, conversations } = get();
        const convo = conversations.find((c) => c.id === activeId);
        if (!convo) return;
        const idx = convo.messages.findIndex((m) => m.id === messageId);
        if (idx === -1) return;
        const truncated = convo.messages.slice(0, idx);
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          createdAt: Date.now(),
          model,
          isStreaming: true
        };
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === activeId ? { ...c, messages: [...truncated, assistantMsg], updatedAt: Date.now() } : c
          )
        }));
        runStream(activeId!, assistantMsg.id, model, undefined, set, get);
      },

      stopGenerating: () => {
        get().abortController?.abort();
        set((s) => ({
          streamingId: null,
          abortController: null,
          conversations: s.conversations.map((c) => ({
            ...c,
            messages: c.messages.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
          }))
        }));
      }
    }),
    {
      name: 'chatui-conversations',
      partialize: (s) => ({ conversations: s.conversations })
    }
  )
);

function runStream(
  conversationId: string,
  assistantId: string,
  model: string,
  options: ChatSendOptions | undefined,
  set: (fn: (s: ChatState) => Partial<ChatState>) => void,
  get: () => ChatState
) {
  const controller = new AbortController();
  set(() => ({ streamingId: assistantId, abortController: controller }));

  const updateMsg = (patch: Partial<Message> | ((m: Message) => Partial<Message>)) => {
    set((s) => ({
      conversations: s.conversations.map((c) => {
        if (c.id !== conversationId) return c;
        return {
          ...c,
          messages: c.messages.map((m) => {
            if (m.id !== assistantId) return m;
            const p = typeof patch === 'function' ? patch(m) : patch;
            return { ...m, ...p };
          })
        };
      })
    }));
  };

  const convo = get().conversations.find((c) => c.id === conversationId);
  const history = (convo?.messages ?? [])
    .filter((m) => m.id !== assistantId)
    .map((m) => ({ role: m.role, content: m.content }));

  const attachmentIds = convo?.messages
    .filter((m) => m.role === 'user')
    .slice(-1)[0]
    ?.attachments?.map((a) => a.id);

  streamChat(
    { model, messages: history, options: { ...options, attachmentIds } },
    {
      onToken: (delta) => updateMsg((m) => ({ content: m.content + delta })),
      onSearchStatus: (status) => updateMsg({ searchStatus: status }),
      onCitations: (citations) => updateMsg({ citations, searchStatus: undefined }),
      onImage: (image) => updateMsg((m) => ({ images: [...(m.images ?? []), image] })),
      onDone: () => {
        updateMsg({ isStreaming: false, searchStatus: undefined });
        set(() => ({ streamingId: null, abortController: null }));
      },
      onError: (err) => {
        updateMsg({ isStreaming: false, error: err.message, searchStatus: undefined });
        set(() => ({ streamingId: null, abortController: null }));
      }
    },
    controller.signal
  );
}
