"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { useRegisterStage } from "@/components/pipeline-state";
import { formatDate } from "@/lib/format";
import type { Article, WordPressState, Job } from "@/types/api";

const labels:Record<string,string>={title:"Title",slug:"Slug",seo_title:"SEO title",meta_description:"Meta description",excerpt:"Excerpt",content:"Treść",approved:"Approval",current_qa:"Aktualne QA",canonical:"Canonical",category:"Category",tags:"Tags",featured_image:"Featured image",schema:"Schema",seo_title_length:"Długość SEO title",meta_description_length:"Długość description"};
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
  const [confirm,setConfirm]=useState<"publish"|"overwrite"|null>(null);
  const load=useCallback(async()=>{
    const next=await api.getWordPress(article.id);setState(next);
    setCategory(next.profile.category);setTags(next.profile.tags.join(", "));
    setAuthor(next.profile.author_id ? String(next.profile.author_id):"");
    setImage(next.profile.featured_image_url??"");setSchema(next.profile.schema_type);
    return next;
  },[article.id]);
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
  useRegisterStage(8,state?.publication?.status==="failed"?"error":["queued","sending"].includes(state?.publication?.status??"")?"running":!removed&&state?.publication?.wordpress_post_id?"success":"neutral",removed?"Wpis usunięty":states[state?.publication?.status??"not_sent"]);
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
  return <section id="workflow-step-8" aria-labelledby="wordpress-title" className="scroll-mt-32 rounded-xl border bg-card p-5 space-y-5">
    <header className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-medium text-muted-foreground">ETAP 8</p><h2 id="wordpress-title" className="text-lg font-semibold">WORDPRESS</h2><p className="text-sm text-muted-foreground">Wersja {article.version} · {removed?"Wpis usunięty w WordPressie":states[state?.publication?.status??"not_sent"]}</p></div>
      <Button variant="outline" disabled={active} onClick={()=>void act(async()=>{const result=await api.testWordPress();toast.success(`Połączenie OK · ${result.capabilities.seo_plugin} · ${result.capabilities.timezone}`);})}>Test connection</Button></header>
    {!approved && <p className="text-sm text-amber-800">Publikacja wymaga approved wersji i aktualnego QA passed.</p>}
    {error&&<p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-900">{error}</p>}
    {state&&<>
      <Button variant="outline" disabled={active} onClick={()=>void act(async()=>{setState(await api.getWordPress(article.id));})}>Sprawdź stan WordPress</Button>
      {removed&&<p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">Wpis został usunięty w WordPressie. Wybierz zatwierdzoną wersję i kliknij „Wyślij ponownie jako draft”, aby umieścić ją w WordPressie.</p>}
      {state.remote_status==="unknown"&&<p className="text-sm text-amber-800">Nie udało się sprawdzić bieżącego stanu WordPressa. Poniżej widoczny jest stan ostatniej synchronizacji.</p>}
      <div aria-label="SEO Preview" className="rounded-lg border p-4 space-y-2"><p className="text-xs text-muted-foreground">SEO Preview</p><p className="break-all text-xs text-emerald-800">{state.profile.canonical_url??`…/${state.profile.slug}/`}</p><p className="text-xl text-sky-800">{state.profile.seo_title||"SEO title wymaga przygotowania"}</p><p className="text-sm leading-6 text-slate-600">{state.profile.meta_description}</p></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm">Category<select aria-label="Category" className={inputClass} value={category} disabled={blocked} onChange={e=>setCategory(e.target.value)}>{state.categories.map(c=><option key={c}>{c}</option>)}</select></label>
        <label className="text-sm">Tags · do 8, oddzielone przecinkami<input className={inputClass} value={tags} disabled={blocked} onChange={e=>setTags(e.target.value)}/></label>
        <label className="text-sm">Author · WordPress user ID<input type="number" min="1" placeholder="Domyślny autor WordPress" className={inputClass} value={author} disabled={blocked} onChange={e=>setAuthor(e.target.value)}/></label>
        <label className="text-sm">Schema<select className={inputClass} value={schema} disabled={blocked} onChange={e=>setSchema(e.target.value)}>{["Article","NewsArticle","TechArticle","HowTo","FAQPage"].map(s=><option key={s}>{s}</option>)}</select></label>
        <label className="text-sm sm:col-span-2">Featured image URL · opcjonalnie<input type="url" className={inputClass} value={image} disabled={blocked} onChange={e=>setImage(e.target.value)}/></label>
      </div>
      <details className="rounded-lg border p-3 text-sm"><summary className="cursor-pointer font-medium">Pełne dane SEO i pre-flight</summary><dl className="mt-3 space-y-2">{[["Canonical",state.profile.canonical_url??"pending — po create"],["Focus keyword",state.profile.focus_keyword||"—"],["Secondary keywords",state.profile.secondary_keywords.join(", ")||"—"],["Excerpt",state.profile.excerpt],["OG title",state.profile.og_title],["OG description",state.profile.og_description],["Twitter/X title",state.profile.twitter_title],["Twitter/X description",state.profile.twitter_description],["Robots",`${state.profile.robots_index?"index":"noindex"}, ${state.profile.robots_follow?"follow":"nofollow"}`]].map(([label,value])=><div key={label}><dt className="font-medium">{label}</dt><dd className="break-words text-muted-foreground">{value}</dd></div>)}</dl>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">{state.checks.map(c=><li key={c.name} className={c.status==="blocked"||c.status==="missing"?"text-rose-800":"text-muted-foreground"}>{labels[c.name]??c.name}: {c.status}{c.value!==undefined?` · ${c.value}`:""}</li>)}</ul>
      </details>
      {state.newer_approved_version_id&&<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"><p>A newer approved version is available.</p>{state.newer_approved_version_id!==article.id&&<Button className="mt-2" variant="outline" onClick={()=>void onSelectVersion(state.newer_approved_version_id!)}>Wybierz zatwierdzoną wersję</Button>}</div>}
      {state.conflict&&<div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"><p>WordPress zawiera inną treść. Synchronizacja wymaga potwierdzenia, aby nie nadpisać jej bez Twojej wiedzy.</p><Button variant="outline" className="mt-2" disabled={blocked} onClick={()=>setConfirm("overwrite")}>Nadpisz sprawdzoną treść WordPress…</Button></div>}
      <p className="text-xs text-muted-foreground">SEO powstaje w kroku 4 razem z artykułem. Wpis w koszu pozostaje bez zmian. Ponowne wysłanie utworzy nowy draft, także po trwałym usunięciu.</p>
      <div className="flex flex-wrap gap-2">
        <Button disabled={blocked||Boolean(state.conflict)} onClick={()=>void act(()=>send("draft"))}>{removed?"Wyślij ponownie jako draft":state.publication?.wordpress_post_id?"Update Draft":"Create Draft"}</Button>
        {state.publication?.wordpress_post_id&&!removed&&<Button disabled={blocked||Boolean(state.conflict)} variant="outline" onClick={()=>void act(async()=>{await saveSettings();setJob(await api.syncWordPress(article.id));await load();})}>Sync to WordPress</Button>}
        <Button disabled={blocked||Boolean(state.conflict)} variant="outline" onClick={()=>setConfirm("publish")}>Publish Now</Button></div>
      <div className="flex flex-wrap items-end gap-3"><label className="text-sm">Schedule · {Intl.DateTimeFormat().resolvedOptions().timeZone}<input type="datetime-local" className={inputClass} value={schedule} disabled={blocked} onChange={e=>setSchedule(e.target.value)}/></label><Button disabled={blocked||!schedule||Boolean(state.conflict)} variant="outline" onClick={()=>void act(()=>send("future"))}>Schedule</Button></div>
      {confirm&&<div role="alertdialog" aria-modal="false" aria-label="Potwierdź operację WordPress" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm space-y-3"><p>{confirm==="publish"?"Opublikować tę zatwierdzoną wersję teraz? Wpis stanie się publiczny.":"Nadpisać obecną treść WordPress zatwierdzoną wersją? Kolejna zmiana w WP ponownie zablokuje sync."}</p><div className="flex gap-2"><Button disabled={blocked} onClick={()=>void act(async()=>{if(confirm==="publish")await send("publish");else{await saveSettings();setJob(await api.syncWordPress(article.id,{expected_wp_hash:state.conflict!.current_hash}));await load();}})}>Potwierdź</Button><Button variant="outline" onClick={()=>setConfirm(null)}>Anuluj</Button></div></div>}
      {state.publication?.wordpress_post_id&&<div className="rounded-lg bg-muted/30 p-4 text-sm space-y-2"><p>WordPress status: <strong>{state.remote_status??state.publication.wp_status}</strong> · Post ID: {state.publication.wordpress_post_id}</p><p>Last synced: {state.publication.last_synced_at?formatDate(state.publication.last_synced_at):"—"}</p><p className="break-all">{state.publication.wordpress_url}</p><div className="flex flex-wrap gap-4">{state.wordpress_admin_url&&!removed&&<a className="underline" target="_blank" rel="noopener" href={state.wordpress_admin_url}>Open in WordPress</a>}{state.publication.wordpress_url&&!removed&&<a className="underline" target="_blank" rel="noopener" href={state.publication.wordpress_url}>Open public URL</a>}</div>{state.publication.wp_status!=="publish"&&<p className="text-muted-foreground">Draft i zaplanowany wpis wymagają uwierzytelnionego podglądu w WordPressie.</p>}</div>}
      {state.publication?.warnings.map(w=><p key={w} className="text-sm text-amber-800">{w}</p>)}
      {job&&<p role="status" className="text-sm text-muted-foreground">Job: {job.status} · {job.stage??"oczekuje"} · próba {job.attempt_count}/{job.max_attempts}</p>}
    </>}
  </section>;
}
