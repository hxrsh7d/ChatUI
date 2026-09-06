import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { Navbar } from '@/components/layout/Navbar';
import { MessageList } from '@/components/chat/MessageList';
import { Placeholder } from '@/components/chat/Placeholder';
import { Composer } from '@/components/composer/Composer';

export function ChatPage() {
  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeId);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const selectedModel = useUIStore((s) => s.selectedModel);
  const webSearchEnabled = useUIStore((s) => s.webSearchEnabled);
  const imageGenEnabled = useUIStore((s) => s.imageGenEnabled);

  const active = conversations.find((c) => c.id === activeId);
  const title = active?.title ?? 'New Chat';
  const hasMessages = (active?.messages.length ?? 0) > 0;

  const onPickSuggestion = (text: string) => {
    sendMessage(text, selectedModel, { webSearch: webSearchEnabled, imageGeneration: imageGenEnabled });
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Navbar title={title} />
      <div className="flex-1 min-h-0 flex flex-col">
        {hasMessages ? <MessageList messages={active!.messages} /> : <Placeholder onPick={onPickSuggestion} />}
      </div>
      <Composer />
    </div>
  );
}
