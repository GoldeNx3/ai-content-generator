import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
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
  table: ({ children }) => <div className="my-5 max-w-full overflow-x-auto rounded border"><table className="w-full border-collapse text-sm">{children}</table></div>,
  th: ({ children, style }) => <th style={style} className="border-b bg-zinc-100 px-4 py-3 text-left font-semibold">{children}</th>,
  td: ({ children, style }) => <td style={style} className="border-b px-4 py-3 align-top">{children}</td>,
  pre: ({ children, node }) => {
    const code = node?.children.find((child) => child.type === "element" && child.tagName === "code");
    const classes = code?.type === "element" ? code.properties.className : [];
    const language = Array.isArray(classes) ? classes.find((name) => typeof name === "string" && name.startsWith("language-"))?.toString().slice(9) : undefined;
    return <div className="my-5 min-w-0 overflow-hidden rounded-lg bg-zinc-900 text-zinc-100">
      <div className="border-b border-zinc-700 px-4 py-2 text-xs text-zinc-400">{language || "Kod"}</div>
      <pre className="overflow-x-auto p-4 text-sm leading-6 [&_code]:rounded-none [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-inherit">{children}</pre>
    </div>;
  },
  code: ({ children, className }) => <code className={`${className || ""} rounded bg-zinc-100 px-1 py-0.5 text-[0.9em]`}>{children}</code>,
};

export function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]} components={COMPONENTS}>{children}</ReactMarkdown>;
}
