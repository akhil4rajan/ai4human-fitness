import ReactMarkdown, { type Components } from "react-markdown";

// react-markdown does not render raw HTML by default, so model output can't inject markup.
const components: Components = {
  p: (p) => <p className="my-2 first:mt-0 last:mb-0" {...p} />,
  ul: (p) => <ul className="my-2 list-disc space-y-1 pl-5" {...p} />,
  ol: (p) => <ol className="my-2 list-decimal space-y-1 pl-5" {...p} />,
  h1: (p) => <h3 className="mt-3 mb-1 text-base font-semibold" {...p} />,
  h2: (p) => <h3 className="mt-3 mb-1 text-base font-semibold" {...p} />,
  h3: (p) => <h4 className="mt-3 mb-1 font-semibold" {...p} />,
  strong: (p) => <strong className="font-semibold" {...p} />,
  a: (p) => <a className="text-accent underline" target="_blank" rel="noopener noreferrer" {...p} />,
  code: (p) => <code className="rounded bg-background px-1 py-0.5 text-sm" {...p} />,
  table: (p) => <div className="my-2 overflow-x-auto"><table className="w-full text-left text-sm" {...p} /></div>,
  th: (p) => <th className="border-b border-border px-2 py-1 font-medium" {...p} />,
  td: (p) => <td className="border-b border-border px-2 py-1" {...p} />,
};

export default function Markdown({ children }: { children: string }) {
  return <ReactMarkdown components={components}>{children}</ReactMarkdown>;
}
