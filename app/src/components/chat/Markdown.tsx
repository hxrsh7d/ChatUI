import { useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Check, Copy } from 'lucide-react';
import 'highlight.js/styles/github-dark.css';

function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const lang = /language-(\w+)/.exec(className ?? '')?.[1] ?? 'text';
  const text = String(children).replace(/\n$/, '');

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between bg-gray-100 dark:bg-gray-850 px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400">
        <span className="font-mono">{lang}</span>
        <button
          onClick={copy}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto bg-gray-950 dark:bg-gray-950 p-3 text-[13px] leading-relaxed">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

export const Markdown = memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ className, children, ...props }: any) {
            const isBlock = /language-/.test(className ?? '');
            if (isBlock) {
              return <CodeBlock className={className}>{children}</CodeBlock>;
            }
            return (
              <code
                className="rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[0.85em] font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre({ children }) {
            return <>{children}</>;
          },
          a(props) {
            return <a {...props} target="_blank" rel="noreferrer" />;
          },
          table({ children, ...props }: any) {
            // GFM tables render at their natural width, which can exceed
            // the message bubble/viewport on mobile and blow out the page
            // layout horizontally. Wrap in a scroll container instead.
            return (
              <div className="my-2 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
                <table {...props} className="w-full">
                  {children}
                </table>
              </div>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
