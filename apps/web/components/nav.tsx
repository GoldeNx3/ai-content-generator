"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { CheckIcon, AlertCircleIcon, Loader2Icon } from "lucide-react";
import { PipelineStateProvider, usePipelineState } from "@/components/pipeline-state";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Tematy" },
  { href: "/sources", label: "Źródła" },
  { href: "/queue", label: "Kolejka" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Nawigacja główna" className="flex min-w-0 gap-1">
      {LINKS.map((link) => {
        const active = link.href === "/" ? pathname === "/" || pathname.startsWith("/candidates") : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={pathname === link.href ? "page" : undefined}
            className={cn(
              "inline-flex min-h-10 items-center rounded-md px-2 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:px-3",
              active ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

const WORKFLOW_LINKS = [
  { href: "#workflow-step-1", label: "Temat" },
  { href: "#workflow-step-2", label: "Ocena tematu" },
  { href: "#workflow-step-3", label: "Research" },
  { href: "#workflow-step-4", label: "Generowanie" },
  { href: "#workflow-step-5", label: "QA / jakość" },
  { href: "#workflow-step-6", label: "Poprawki i zatwierdzenie" },
  { href: "#workflow-step-8", label: "WordPress" },
];

export function CandidateScreen({ children }: { children: React.ReactNode }) {
  return <PipelineStateProvider><PipelineScreen>{children}</PipelineScreen></PipelineStateProvider>;
}
function PipelineScreen({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState("#workflow-step-1");
  useEffect(() => {
    const sync = () => {
      const hash = window.location.hash;
      const target = WORKFLOW_LINKS.find(link => link.href === hash)?.href;
      if (target) setActive(target);
      else if (hash.startsWith("#article-")) setActive("#workflow-step-4");
    };
    const read = () => setActive("#workflow-step-4");
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("article-workspace-read", read);
    return () => { window.removeEventListener("hashchange", sync); window.removeEventListener("article-workspace-read", read); };
  }, []);
  return <div className="candidate-screen min-w-0 space-y-6" data-view={active.slice(1)}>
    <PipelineStepper active={active} onSelect={setActive} />
    {children}
  </div>;
}

function PipelineStepper({ active, onSelect }: { active: string; onSelect: (href: string) => void }) {
  const states = usePipelineState()?.stages ?? {};
  const current = Math.max(0, WORKFLOW_LINKS.findIndex(link => link.href === active));
  return <nav aria-label="Nawigacja po temacie i artykule" className="sticky top-14 z-20 min-w-0 rounded-xl bg-zinc-50/95 py-3 backdrop-blur">
    <div className="space-y-3 lg:hidden">
      <label className="flex items-center justify-between gap-4 text-sm"><span className="shrink-0 font-medium text-emerald-800">{WORKFLOW_LINKS[current].label} · {current + 1} z {WORKFLOW_LINKS.length}</span>
        <select aria-label="Wybierz etap pipeline" value={active} className="min-h-11 min-w-0 flex-1 rounded-lg border bg-white px-3 font-medium" onChange={event => {onSelect(event.target.value);window.location.hash=event.target.value;}}>
          {WORKFLOW_LINKS.map(link => <option key={link.href} value={link.href}>{link.label}</option>)}
        </select>
      </label>
      <div aria-hidden="true" className="grid grid-cols-7 gap-1">{WORKFLOW_LINKS.map((link,index) => <span key={link.href} className={cn("h-1.5 rounded-full",index===current?"bg-emerald-700":states[Number(link.href.split("-").at(-1))]?.tone==="success"?"bg-emerald-300":"bg-slate-200")} />)}</div>
    </div>
    <ol className="hidden items-start gap-2 lg:flex">
      {WORKFLOW_LINKS.map((link,index) => {
        const state=states[Number(link.href.split("-").at(-1))];const selected=active===link.href;
        const Icon=state?.tone==="success"?CheckIcon:state?.tone==="error"||state?.tone==="attention"?AlertCircleIcon:state?.tone==="running"?Loader2Icon:null;
        return <li key={link.href} className="flex min-w-0 flex-1 items-center gap-2 last:flex-[1.25]">
          <a aria-label={link.label} href={link.href} aria-current={selected?"step":undefined} title={state?.status??"Oczekuje"} onClick={()=>onSelect(link.href)} className="group flex min-h-12 min-w-0 items-center gap-2 rounded-lg px-1 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">
            <span data-step-status={selected?"current":state?.tone??"neutral"} className={cn("flex size-9 shrink-0 items-center justify-center rounded-full text-sm",selected?"bg-emerald-700 text-white":state?.tone==="success"?"bg-emerald-100 text-emerald-800":state?.tone==="error"?"bg-rose-100 text-rose-800":state?.tone==="attention"?"bg-amber-100 text-amber-900":state?.tone==="running"?"bg-sky-100 text-sky-900":"bg-slate-100 text-slate-500")}>
              {Icon?<Icon className={cn("size-4",state?.tone==="running"&&"animate-spin")} />:Number(link.href.split("-").at(-1))}
            </span><span className={cn("leading-5",selected?"font-semibold text-emerald-800":state?.tone==="success"?"text-emerald-800":"text-slate-600 group-hover:text-foreground")}>{link.label}</span>
          </a>
          {index<WORKFLOW_LINKS.length-1&&<span aria-hidden="true" className="h-px min-w-2 flex-1 bg-slate-200" />}
        </li>;
      })}
    </ol>
  </nav>;
}
