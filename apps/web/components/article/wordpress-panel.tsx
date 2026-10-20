"use client";
import Link from "next/link";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api, errorText, ERROR_MESSAGES } from "@/lib/api";
import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { formatDate } from "@/lib/format";
import type { Article, WordPressState, Job } from "@/types/api";

const labels:Record<string,string>={title:"Title",slug:"Slug",seo_title:"SEO title",meta_description:"Meta description",excerpt:"Zajawka",content:"Treść",approved:"Approval",current_qa:"Aktualne QA",canonical:"Canonical",category:"Category",tags:"Tags",featured_image:"Featured image",schema:"Schema",seo_title_length:"Długość SEO title",meta_description_length:"Długość description"};
const states:Record<string,string>={not_sent:"Nie wysłano",queued:"W kolejce",sending:"Wysyłanie",draft_created:"Draft utworzony",scheduled:"Zaplanowano",published:"Opublikowano",failed:"Błąd"};
const inputClass="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm";

export function WordPressPanel({article,onSelectVersion,editing}:{article:Article;onSelectVersion:(id:number)=>Promise<void>;editing:boolean}) {
  const [state,setState]=useState<WordPressState|null>(null);
  const [job,setJob]=useState<Job|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [category,setCategory]=useState("");
  const [tags,setTags]=useState("");
  const [author,setAuthor]=useState("");
  const [image,setImage]=useState("");
  const [schema,setSchema]=useState("Article");
  const [schedule,setSchedule]=useState("");
  const confirmationRef = useRef<HTMLDivElement>(null);
  const [confirm,setConfirm]=useState<"publish"|"overwrite"|null>(null);
  useEffect(() => {
    if (!confirm) return;
    confirmationRef.current?.focus({ preventScroll: true });
    confirmationRef.current?.scrollIntoView({ block: "nearest" });
  }, [confirm]);
  const load=useCallback(async()=>{
    const next=await api.getWordPress(article.id);setState(next);
    setCategory(next.profile.category);setTags(next.profile.tags.join(", "));
    setAuthor(next.profile.author_id ? String(next.profile.author_id):"");
    setImage(next.profile.featured_image_url??"");setSchema(next.profile.schema_type);
    return next;
  },[article.id]);
  const publicationJobs = useCandidateJobs(article.candidate_id, "publish_wordpress", async () => { await load(); return true; }, article.id);
  useEffect(()=>{
    let alive=true;
    api.getWordPress(article.id).then(next=>{
      if(!alive)return;setState(next);setCategory(next.profile.category);setTags(next.profile.tags.join(", "));
      setAuthor(next.profile.author_id?String(next.profile.author_id):"");setImage(next.profile.featured_image_url??"");setSchema(next.profile.schema_type);
    }).catch(e=>alive&&setError(errorText(e)));
    return()=>{alive=false;};
  },[article.id,article.status]);
  useEffect(()=>{
    if(!job || !["queued","running","retrying"].includes(job.status))return;
    let alive=true;
    const timer=setInterval(()=>{void api.getJob(job.id).then(async next=>{
      if(!alive)return;setJob(next);
      if(next.status==="succeeded" || next.status==="failed") {
        await load();setError(next.status==="failed"?next.error_message:null);
      }
    }).catch(e=>alive&&setError(errorText(e)));},1500);
    return()=>{alive=false;clearInterval(timer);};
  },[job,load]);
  // Refresh persisted publication jobs after navigating back or reopening the page.
  useEffect(()=>{
    if(!state || !["queued","sending"].includes(state.publication?.status??""))return;
    const timer=setInterval(()=>{void load().catch(e=>setError(errorText(e)));},2000);
    return()=>clearInterval(timer);
  },[state,load]);
  const removed=state?.remote_status==="trash" || state?.remote_status==="missing";

  const active=busy || editing || Boolean(job&&["queued","running","retrying"].includes(job.status)) || ["queued","sending"].includes(state?.publication?.status??"");
  useEffect(()=>{
    const refresh=()=>{if(!active)void api.getWordPress(article.id).then(setState).catch(e=>setError(errorText(e)));};
    window.addEventListener("focus",refresh);
    return()=>window.removeEventListener("focus",refresh);
  },[active,article.id]);
  const approved=article.status==="approved";
  const blocked=active || !approved || !state?.qa_ok;
  async function act(action:()=>Promise<unknown>) {
    setBusy(true);setError(null);
    try {await action();}
    catch(e){setError(errorText(e));toast.error("WordPress",{description:errorText(e)});}
    finally{setBusy(false);setConfirm(null);}
  }
  async function saveSettings(){
    await api.setWordPressSettings(article.id,{category,tags:tags.split(",").map(t=>t.trim()).filter(Boolean),author_id:author?Number(author):null,featured_image_url:image||null,schema_type:schema});
  }
  async function send(status:"draft"|"future"|"publish") {
    let scheduled_at:string|undefined;
    if(status==="future") {
      const date=new Date(schedule);
      if(!schedule||Number.isNaN(date.getTime())||date.getTime()<=Date.now())throw new Error("Wybierz przyszłą datę publikacji.");
      scheduled_at=date.toISOString();
    }
    await saveSettings();setJob(await api.publishWordPress(article.id,{status,scheduled_at}));await load();
  }
  return <WorkflowSection progressJob={publicationJobs.ownActive ?? job ?? undefined} tone={state?.publication?.status === "failed" ? "error" : ["queued", "sending"].includes(state?.publication?.status ?? "") ? "running" : !removed && state?.publication?.wordpress_post_id ? "success" : "neutral"} number={8} title="Publikacja w WordPressie" paid={false}
    status={removed ? "Wpis usunięty" : states[state?.publication?.status ?? "not_sent"]}
    description={`Ustawienia publikacji i wysyłka wybranej wersji ${article.version}.`}
    actionTitle="Publikacja" actionDescription="Zapisz szkic, zsynchronizuj istniejący wpis lub wybierz termin publikacji."
    actions={<>
      <p className="action-hint">{editing ? "Zapisz lub anuluj edycję przed publikacją." : !approved ? "Zatwierdź tę wersję po zaliczonym QA, aby odblokować publikację." : !state?.qa_ok ? "Wymagane aktualne, zaliczone QA tej wersji." : active ? "Trwa operacja WordPress. Poczekaj na jej zakończenie." : "Wybrana wersja spełnia warunki publikacji."}</p>
      {state ? <>
      <div className="grid gap-3">
        <Button variant={state.publication?.wordpress_post_id && !removed ? "outline" : "default"} disabled={blocked||Boolean(state.conflict)} onClick={()=>void act(()=>send("draft"))}>{removed?"Utwórz ponownie szkic":state.publication?.wordpress_post_id?"Zapisz wpis jako szkic":"Utwórz szkic w WordPressie"}</Button>
        <Button disabled={blocked||Boolean(state.conflict)||!state.publication?.wordpress_post_id||removed} variant={state.publication?.wordpress_post_id && !removed ? "default" : "outline"} onClick={()=>void act(async()=>{await saveSettings();setJob(await api.syncWordPress(article.id));await load();})}>Synchronizuj z WordPressem</Button>
        <Button disabled={blocked||Boolean(state.conflict)} variant="outline" onClick={()=>setConfirm("publish")}>Opublikuj teraz</Button></div>
      <div className="action-group grid gap-3"><label className="text-sm">Termin publikacji · {Intl.DateTimeFormat().resolvedOptions().timeZone}<input type="datetime-local" className={inputClass} value={schedule} disabled={blocked} onChange={e=>setSchedule(e.target.value)}/></label><Button disabled={blocked||!schedule||Boolean(state.conflict)} variant="outline" onClick={()=>void act(()=>send("future"))}>Zaplanuj publikację</Button></div>
      <p className="action-hint">Zapis jako szkic wycofuje publiczną lub zaplanowaną publikację. Synchronizacja zachowuje stan istniejącego wpisu.</p>
      {confirm&&<div ref={confirmationRef} tabIndex={-1} role="alertdialog" aria-modal="false" aria-label="Potwierdź operację WordPress" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm space-y-3"><p>{confirm==="publish"?"Opublikować tę zatwierdzoną wersję teraz? Wpis stanie się publiczny.":"Nadpisać obecną treść WordPress zatwierdzoną wersją? Kolejna zmiana w WP ponownie zablokuje sync."}</p><div className="grid min-w-0 grid-cols-1 gap-2"><Button disabled={blocked} onClick={()=>void act(async()=>{if(confirm==="publish")await send("publish");else{await saveSettings();setJob(await api.syncWordPress(article.id,{expected_wp_hash:state.conflict!.current_hash}));await load();}})}>Potwierdź</Button><Button variant="outline" onClick={()=>setConfirm(null)}>Anuluj</Button></div></div>}
      </> : <><Button disabled>Utwórz szkic w WordPressie</Button><Button variant="outline" disabled>Opublikuj teraz</Button><Button variant="outline" disabled>Zaplanuj publikację</Button></>}
      <div className="action-group">
<Button variant="outline" disabled={active} onClick={()=>void act(async()=>{const result=await api.testWordPressConnection();if(result.last_error)throw new Error(ERROR_MESSAGES[result.last_error]??result.last_error);toast.success(`Połączenie OK · ${result.site_url}`);})}>Sprawdź połączenie</Button>
        <Button variant="outline" disabled={active} onClick={()=>void act(async()=>{setState(await api.getWordPress(article.id));})}>Sprawdź stan WordPress</Button>
      </div>
    </>}
    summary={<UsageSummary free note="Wysyłka artykułu nie wywołuje AI. Opublikowanie wpisu wymaga osobnej decyzji." />}>
    {error&&<p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}
    {state&&!state.wordpress_connected&&<p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">WordPress nie jest połączony z tym workspace&apos;em. <Link href="/settings" className="font-medium underline underline-offset-4">Połącz stronę w Ustawieniach</Link>, aby wysyłać artykuły.</p>}
    {state&&<>
      {removed&&<p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">Wpis został usunięty w WordPressie. Wybierz zatwierdzoną wersję i kliknij „Utwórz ponownie szkic”, aby umieścić ją w WordPressie.</p>}
      {state.remote_status==="unknown"&&<p className="text-sm text-amber-800">Nie udało się sprawdzić bieżącego stanu WordPressa. Poniżej widoczny jest stan ostatniej synchronizacji.</p>}
      <div aria-label="Podgląd w wyszukiwarce" className="rounded-lg border p-4 space-y-2"><p className="text-xs text-muted-foreground">Podgląd w wyszukiwarce</p><p className="break-all text-xs text-emerald-800">{state.profile.canonical_url??`…/${state.profile.slug}/`}</p><p className="text-xl text-sky-800">{state.profile.seo_title||"Tytuł SEO wymaga przygotowania"}</p><p className="text-sm leading-6 text-slate-600">{state.profile.meta_description}</p></div>
      <div className="grid gap-4 rounded-xl border bg-muted/20 p-5 sm:grid-cols-2">
        <label className="text-sm">Kategoria<select aria-label="Kategoria" className={inputClass} value={category} disabled={blocked} onChange={e=>setCategory(e.target.value)}>{state.categories.map(c=><option key={c}>{c}</option>)}</select></label>
        <label className="text-sm">Tagi · maks. 8, oddziel przecinkami<input className={inputClass} value={tags} disabled={blocked} onChange={e=>setTags(e.target.value)}/></label>
        <label className="text-sm">Autor · identyfikator w WordPressie<input type="number" min="1" placeholder="Domyślny autor WordPress" className={inputClass} value={author} disabled={blocked} onChange={e=>setAuthor(e.target.value)}/></label>
        <label className="text-sm">Typ danych strukturalnych<select className={inputClass} value={schema} disabled={blocked} onChange={e=>setSchema(e.target.value)}>{["Article","NewsArticle","TechArticle","HowTo","FAQPage"].map(s=><option key={s}>{s}</option>)}</select></label>
        <label className="text-sm sm:col-span-2">Adres obrazu wyróżniającego · opcjonalnie<input type="url" className={inputClass} value={image} disabled={blocked} onChange={e=>setImage(e.target.value)}/></label>
      </div>
      <details className="rounded-lg border p-3 text-sm"><summary className="cursor-pointer font-medium">Dane SEO i wymagania publikacji</summary><dl className="mt-3 space-y-2">{[["Canonical",state.profile.canonical_url??"Po utworzeniu wpisu"],["Główna fraza",state.profile.focus_keyword||"—"],["Dodatkowe frazy",state.profile.secondary_keywords.join(", ")||"—"],["Zajawka",state.profile.excerpt],["OG title",state.profile.og_title],["OG description",state.profile.og_description],["Twitter/X title",state.profile.twitter_title],["Twitter/X description",state.profile.twitter_description],["Robots",`${state.profile.robots_index?"index":"noindex"}, ${state.profile.robots_follow?"follow":"nofollow"}`]].map(([label,value])=><div key={label}><dt className="font-medium">{label}</dt><dd className="break-words text-muted-foreground">{value}</dd></div>)}</dl>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">{state.checks.map(c=><li key={c.name} className={c.status==="blocked"||c.status==="missing"?"text-rose-800":"text-muted-foreground"}>{labels[c.name]??c.name}: {c.status}{c.value!==undefined?` · ${c.value}`:""}</li>)}</ul>
      </details>
      {state.newer_approved_version_id&&<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"><p>Dostępna jest nowsza zatwierdzona wersja.</p>{state.newer_approved_version_id!==article.id&&<Button className="mt-2" variant="outline" onClick={()=>void onSelectVersion(state.newer_approved_version_id!)}>Wybierz zatwierdzoną wersję</Button>}</div>}
      {state.conflict&&<div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"><p>WordPress zawiera inną treść. Synchronizacja wymaga potwierdzenia, aby nie nadpisać jej bez Twojej wiedzy.</p><Button variant="outline" className="mt-2" disabled={blocked} onClick={()=>setConfirm("overwrite")}>Nadpisz sprawdzoną treść WordPress…</Button></div>}
      <p className="text-xs text-muted-foreground">SEO powstaje w kroku 4 razem z artykułem. Wpis w koszu pozostaje bez zmian. Ponowne wysłanie utworzy nowy szkic, także po trwałym usunięciu.</p>
      {state.publication?.wordpress_post_id&&<div className="rounded-lg bg-muted/30 p-4 text-sm space-y-2"><p>WordPress status: <strong>{state.remote_status??state.publication.wp_status}</strong> · Post ID: {state.publication.wordpress_post_id}</p><p>Ostatnia synchronizacja: {state.publication.last_synced_at?formatDate(state.publication.last_synced_at):"—"}</p><p className="break-all">{state.publication.wordpress_url}</p><div className="flex flex-wrap gap-4">{state.wordpress_admin_url&&!removed&&<a className="underline" target="_blank" rel="noopener" href={state.wordpress_admin_url}>Otwórz w WordPressie</a>}{state.publication.wordpress_url&&!removed&&<a className="underline" target="_blank" rel="noopener" href={state.publication.wordpress_url}>Otwórz stronę wpisu</a>}</div>{state.publication.wp_status!=="publish"&&<p className="text-muted-foreground">Szkic i zaplanowany wpis wymagają uwierzytelnionego podglądu w WordPressie.</p>}</div>}
      {state.publication?.warnings.map(w=><p key={w} className="text-sm text-amber-800">{w}</p>)}
      {job&&<p role="status" className="text-sm text-muted-foreground">Job: {job.status} · {job.stage??"oczekuje"} · próba {job.attempt_count}/{job.max_attempts}</p>}
    </>}
  </WorkflowSection>;
}
