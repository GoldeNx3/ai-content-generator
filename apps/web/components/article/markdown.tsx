import ReactMarkdown, { type Components } from "react-markdown";

// Styling without a typography plugin. Raw HTML in Markdown is not rendered (react-markdown default).
const COMPONENTS: Components = {
  h2: ({ children }) => <h2 className="mt-8 mb-3 text-xl font-semibold tracking-tight">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-6 mb-2 text-lg font-semibold">{children}</h3>,
  p: ({ children }) => <p className="my-3 leading-7">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-emerald-700 underline">
      {children}
    </a>
  ),
  blockquote: ({ children }) => <blockquote className="my-3 border-l-2 pl-4 text-muted-foreground">{children}</blockquote>,
  code: ({ children }) => <code className="rounded bg-zinc-100 px-1 py-0.5 text-[0.9em]">{children}</code>,
};

export function Markdown({ children }: { children: string }) {
  return <ReactMarkdown components={COMPONENTS}>{children}</ReactMarkdown>;
}
