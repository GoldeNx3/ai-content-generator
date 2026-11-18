"use client";
import Link from "next/link";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { CheckIcon, ExternalLinkIcon, GlobeIcon, ListChecksIcon, PlugIcon, SearchIcon, SlidersHorizontalIcon } from "lucide-react";
import { ResultBlock, ResultOutline, setResultBlock } from "@/components/stage/result-block";
import { navigateStage } from "@/components/pipeline-state";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorText, ERROR_MESSAGES } from "@/lib/api";
import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { formatDate } from "@/lib/format";
import { stageLabel } from "@/lib/jobs";
import { jobStatusLabel } from "@/components/job-status";
import type { Article, WordPressState, Job } from "@/types/api";

const labels:Record<string,string>={title:"Tytuł",slug:"Slug (adres)",seo_title:"Tytuł SEO",meta_description:"Opis meta",excerpt:"Zajawka",content:"Treść",approved:"Zatwierdzenie",current_qa:"Aktualne QA",canonical:"Adres kanoniczny",category:"Kategoria",tags:"Tagi",featured_image:"Obraz wyróżniający",schema:"Dane strukturalne",seo_title_length:"Długość tytułu SEO (50–60)",meta_description_length:"Długość opisu meta (140–160)"};
const checkStates:Record<string,{label:string;className:string}>={ok:{label:"OK",className:"text-emerald-700"},missing:{label:"Brak",className:"text-rose-800"},blocked:{label:"Blokuje",className:"text-rose-800"},pending:{label:"Po utworzeniu wpisu",className:"text-muted-foreground"},optional_missing:{label:"Brak (opcjonalne)",className:"text-muted-foreground"},warning:{label:"Do poprawy",className:"text-amber-800"}};
const states:Record<string,string>={not_sent:"Nie wysłano",queued:"W kolejce",sending:"Wysyłanie",draft_created:"Draft utworzony",scheduled:"Zaplanowano",published:"Opublikowano",failed:"Błąd"};
const inputClass="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm";

export function WordPressPanel({article,onSelectVersion,editing,onEdit}:{article:Article;onSelectVersion:(id:number)=>Promise<void>;editing:boolean;onEdit:(field?:string)=>void}) {
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
    confirmationRef.current?.scrollIntoView({ block: "center" });
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
      if(next.status==="succeeded" || next.status==="failed" || next.status==="cancelled") {
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
  const hasPost=Boolean(state?.publication?.wordpress_post_id);
  const okChecks=state?.checks.filter(c=>c.status==="ok").length??0;
  const problemChecks=state?.checks.filter(c=>["missing","blocked","warning"].includes(c.status)).length??0;
  const editVersion=(field:string)=>({label:"Popraw w edytorze artykułu",disabled:editing,run:()=>onEdit(field)});
  const openSettings={label:"Przejdź do ustawień wpisu",run:()=>{setResultBlock("wp-settings", true, false);requestAnimationFrame(()=>document.getElementById("wp-settings")?.scrollIntoView({behavior:"smooth",block:"start"}));}};
  const newVersionNote="Zapis w edytorze utworzy nową wersję — potem uruchom jej QA i zatwierdź ją, zanim ją wyślesz.";
  function checkFix(name:string,status:string,profile:WordPressState["profile"]):{text:string;current?:string;action?:{label:string;disabled?:boolean;run:()=>void}} {
    switch(name){
      case "seo_title_length": return {current:profile.seo_title,text:`Tytuł SEO to pole „Meta title” wersji artykułu. Google pokazuje zwykle 50–60 znaków; krótszy tytuł marnuje miejsce, dłuższy zostanie ucięty. To zalecenie — nie blokuje wysyłki. ${newVersionNote}`,action:editVersion("meta_title")};
      case "meta_description_length": return {current:profile.meta_description,text:`Opis meta to pole „Meta description” wersji artykułu. Najlepiej 140–160 znaków; krótszy opis Google może zastąpić fragmentem tekstu. To zalecenie — nie blokuje wysyłki. ${newVersionNote}`,action:editVersion("meta_description")};
      case "seo_title": case "meta_description": return {text:`Puste pole system uzupełni modelem AI przy wysyłce. Możesz też wpisać je samodzielnie w polu „${name==="seo_title"?"Meta title":"Meta description"}”. ${newVersionNote}`,action:editVersion(name==="seo_title"?"meta_title":"meta_description")};
      case "title": case "content": return {text:`Uzupełnij w edytorze artykułu. ${newVersionNote}`,action:editVersion(name)};
      case "slug": case "excerpt": return {text:"Puste pole system uzupełni przy wysyłce na podstawie artykułu."};
      case "approved": return {text:"Wysłać można tylko zatwierdzoną wersję.",action:{label:"Przejdź do zatwierdzenia",run:()=>navigateStage(6)}};
      case "current_qa": return {text:"Ta wersja potrzebuje aktualnego, zaliczonego QA.",action:{label:"Przejdź do QA",run:()=>navigateStage(5)}};
      case "category": return {text:"Wybierz kategorię z listy dozwolonych w ustawieniach wpisu.",action:openSettings};
      case "featured_image": return {text:"Opcjonalne. Dodaj adres obrazu w ustawieniach wpisu, jeśli wpis ma mieć obraz wyróżniający.",action:openSettings};
      case "canonical": return {text:"Ustali się automatycznie, gdy WordPress utworzy wpis."};
      default: return {text:status==="blocked"?"To wymaganie blokuje wysyłkę.":"Sprawdź to pole przed wysyłką."};
    }
  }
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
  return <WorkflowSection progressJob={publicationJobs.ownActive ?? job ?? undefined} tone={state?.publication?.status === "failed" ? "error" : ["queued", "sending"].includes(state?.publication?.status ?? "") ? "running" : !removed && state?.publication?.wordpress_post_id ? "success" : "neutral"} number={8} title="Publikacja w WordPressie" paid={false} resultTitle="Wpis w WordPressie"
    status={removed ? "Wpis usunięty" : states[state?.publication?.status ?? "not_sent"]}
    description={`Ustawienia publikacji i wysyłka wybranej wersji ${article.version}.`}
    actionTitle="Publikacja" actionDescription="Wyślij wybraną wersję jako szkic, zsynchronizuj istniejący wpis albo zaplanuj publikację."
    actionDetails={!editing && approved && state?.qa_ok && !active ? <p className="text-sm text-emerald-800">Wersja {article.version} spełnia warunki publikacji.</p> : undefined}
    blocker={editing ? "Zapisz lub anuluj edycję przed publikacją." : !approved ? "Zatwierdź tę wersję po zaliczonym QA, aby odblokować publikację." : state && !state.qa_ok ? "Wymagane aktualne, zaliczone QA tej wersji." : active ? "Trwa operacja WordPress. Poczekaj na jej zakończenie." : state && !state.wordpress_connected ? "WordPress nie jest połączony. Połącz stronę w Ustawieniach → Integracje." : undefined}
    primary={state ? <>
      <Button variant={state.publication?.wordpress_post_id && !removed ? "outline" : "default"} disabled={blocked||Boolean(state.conflict)} onClick={()=>void act(()=>send("draft"))}>{removed?"Utwórz ponownie szkic":state.publication?.wordpress_post_id?"Zapisz wpis jako szkic":"Utwórz szkic w WordPressie"}</Button>
      <Button disabled={blocked||Boolean(state.conflict)||!state.publication?.wordpress_post_id||removed} variant={state.publication?.wordpress_post_id && !removed ? "default" : "outline"} onClick={()=>void act(async()=>{await saveSettings();setJob(await api.syncWordPress(article.id));await load();})}>Synchronizuj z WordPressem</Button>
      <Button disabled={blocked||Boolean(state.conflict)} variant="outline" onClick={()=>setConfirm("publish")}>Opublikuj teraz</Button>
      <p className="action-hint">Zapis jako szkic wycofuje publiczną lub zaplanowaną publikację. Synchronizacja zachowuje stan istniejącego wpisu.</p>
      {confirm&&<div ref={confirmationRef} tabIndex={-1} role="alertdialog" aria-modal="false" aria-label="Potwierdź operację WordPress" className="space-y-3 rounded-lg bg-amber-50 p-4 text-sm ring-1 ring-amber-200"><p>{confirm==="publish"?"Opublikować tę zatwierdzoną wersję teraz? Wpis stanie się publiczny.":"Nadpisać obecną treść WordPress zatwierdzoną wersją? Kolejna zmiana w WP ponownie zablokuje synchronizację."}</p><div className="grid min-w-0 grid-cols-1 gap-2"><Button disabled={blocked} onClick={()=>void act(async()=>{if(confirm==="publish")await send("publish");else{await saveSettings();setJob(await api.syncWordPress(article.id,{expected_wp_hash:state.conflict!.current_hash}));await load();}})}>Potwierdź</Button><Button variant="outline" onClick={()=>setConfirm(null)}>Anuluj</Button></div></div>}
    </> : <><Button disabled>Utwórz szkic w WordPressie</Button><Button variant="outline" disabled>Opublikuj teraz</Button></>}
    secondaryTitle="Planowanie"
    secondary={<>
      <label className="text-sm">Termin publikacji · {Intl.DateTimeFormat().resolvedOptions().timeZone}<input type="datetime-local" className={inputClass} value={schedule} disabled={blocked||!state} onChange={e=>setSchedule(e.target.value)}/></label>
      <Button disabled={blocked||!state||!schedule||Boolean(state?.conflict)} variant="outline" onClick={()=>void act(()=>send("future"))}>Zaplanuj publikację</Button>
    </>}
    toolsTitle="Diagnostyka"
    tools={<>
      <Button variant="outline" disabled={active} onClick={()=>void act(async()=>{const result=await api.testWordPressConnection();if(result.last_error)throw new Error(ERROR_MESSAGES[result.last_error]??result.last_error);toast.success(`Połączenie OK · ${result.site_url}`);})}>Sprawdź połączenie</Button>
      <Button variant="outline" disabled={active} onClick={()=>void act(async()=>{setState(await api.getWordPress(article.id));})}>Sprawdź stan WordPress</Button>
    </>}
    navigationTitle="Koniec procesu"
    navigation={<Link href="/" className={buttonVariants({variant:"outline"})}>Wróć do listy tematów</Link>}
    summary={<UsageSummary free note="Wysyłka zwykle nie wywołuje AI. Gdy brakuje pól SEO (tytuł, opis, slug, zajawka), system uzupełnia je modelem AI — ten krok nie jest blokowany przez budżet. Opublikowanie wpisu wymaga osobnej decyzji." />}>
    <div className="space-y-6">
    {article.refresh_of && <p role="note" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">To aktualizacja wpisu {article.refresh_of.url ? <a href={article.refresh_of.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">„{article.refresh_of.title}”</a> : `„${article.refresh_of.title}”`}. Publikacja utworzy nowy szkic; po sprawdzeniu przenieś treść do starego wpisu albo przekieruj jego adres.</p>}
    {error&&<p role="alert" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-900 ring-1 ring-rose-200">{error}</p>}
    {state&&!state.wordpress_connected&&<p role="status" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">WordPress nie jest połączony z tym workspace&apos;em. <Link href="/settings" className="font-medium underline underline-offset-4">Połącz stronę w Ustawieniach</Link>, aby wysyłać artykuły.</p>}
    {!state&&!error&&<p className="text-sm text-muted-foreground">Wczytywanie stanu publikacji…</p>}
    {state&&<>
      {removed&&<p role="status" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">Wpis został usunięty w WordPressie. Wybierz zatwierdzoną wersję i kliknij „Utwórz ponownie szkic”, aby umieścić ją w WordPressie.</p>}
      {state.remote_status==="unknown"&&<p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">Nie udało się sprawdzić bieżącego stanu WordPressa. Poniżej widoczny jest stan ostatniej synchronizacji.</p>}
      {state.newer_approved_version_id&&<div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200"><p>Dostępna jest nowsza zatwierdzona wersja.</p>{state.newer_approved_version_id!==article.id&&<Button className="mt-2" variant="outline" onClick={()=>void onSelectVersion(state.newer_approved_version_id!)}>Wybierz zatwierdzoną wersję</Button>}</div>}
      {state.conflict&&<div role="alert" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200"><p>WordPress zawiera inną treść. Synchronizacja wymaga potwierdzenia, aby nie nadpisać jej bez Twojej wiedzy.</p><Button variant="outline" className="mt-2" disabled={blocked} onClick={()=>setConfirm("overwrite")}>Nadpisz sprawdzoną treść WordPress…</Button></div>}
      {state.publication?.warnings.map(w=><p key={w} className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">{w}</p>)}
      {job&&<p role="status" className="text-sm text-muted-foreground">Zadanie WordPress: {jobStatusLabel[job.status]} · {stageLabel(job.stage)} · próba {job.attempt_count}/{job.max_attempts}</p>}

      <ResultOutline label="Stan publikacji" meta="Brakujące pola SEO system uzupełni przy wysyłce." items={[
        { target: hasPost ? "wp-post" : "wp-settings", label: "Wpis", value: removed ? "Usunięty" : states[state.publication?.status ?? "not_sent"], hint: hasPost ? `ID ${state.publication!.wordpress_post_id}` : "jeszcze nie wysłano", icon: GlobeIcon, tone: state.publication?.status === "failed" || removed ? "danger" : hasPost ? "success" : "neutral" },
        { target: "wp-checks", label: "Wymagania", value: state.checks.length ? `${okChecks}/${state.checks.length}` : "—", hint: !state.checks.length ? "sprawdzane po zatwierdzeniu" : problemChecks ? `${problemChecks} do sprawdzenia` : "spełnione", icon: ListChecksIcon, tone: !state.checks.length ? "neutral" : problemChecks ? "attention" : "success" },
        { target: "wp-seo", label: "Tytuł SEO", value: state.profile.seo_title ? state.profile.seo_title.length : "—", hint: "znaków · zalecane 50–60", icon: SearchIcon, tone: state.profile.seo_title && state.profile.seo_title.length >= 50 && state.profile.seo_title.length <= 60 ? "success" : "attention" },
        { target: "wp-settings", label: "Połączenie", value: state.wordpress_connected ? "Aktywne" : "Brak", hint: state.wordpress_connected ? "WordPress połączony" : "Ustawienia → Integracje", icon: PlugIcon, tone: state.wordpress_connected ? "success" : "danger" },
      ]} />

      {hasPost&&<ResultBlock id="wp-post" icon={GlobeIcon} title="Wpis w WordPressie"
        description="Stan wpisu po stronie WordPressa i odnośniki do niego. Szkic i zaplanowany wpis wymagają zalogowania w WordPressie.">
        <dl className="divide-y rounded-xl bg-muted/40 px-4 text-sm">
          {([["Status w WordPressie", state.remote_status??state.publication!.wp_status], ["Post ID", String(state.publication!.wordpress_post_id)], ["Ostatnia synchronizacja", state.publication!.last_synced_at?formatDate(state.publication!.last_synced_at):"—"], ["Adres wpisu", state.publication!.wordpress_url??"—"]] as const).map(([label,value])=>
            <div key={label} className="grid gap-1 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4"><dt className="font-medium text-muted-foreground">{label}</dt><dd className="break-all">{value}</dd></div>)}
        </dl>
        {!removed&&<div className="flex flex-wrap gap-2">{state.wordpress_admin_url&&<a className={buttonVariants({variant:"outline",size:"sm"})} target="_blank" rel="noopener" href={state.wordpress_admin_url}><ExternalLinkIcon />Otwórz w WordPressie</a>}{state.publication!.wordpress_url&&<a className={buttonVariants({variant:"outline",size:"sm"})} target="_blank" rel="noopener" href={state.publication!.wordpress_url}><ExternalLinkIcon />Otwórz stronę wpisu</a>}</div>}
      </ResultBlock>}

      <ResultBlock id="wp-settings" icon={SlidersHorizontalIcon} title="Ustawienia wpisu"
        description="Kategoria, tagi, autor i obraz, z którymi wpis trafi do WordPressa. Zapisują się przy każdej wysyłce.">
        <div className="grid gap-4 rounded-xl bg-muted/40 p-4 sm:grid-cols-2">
          <label className="text-sm font-medium">Kategoria<select aria-label="Kategoria" className={inputClass} value={category} disabled={blocked} onChange={e=>setCategory(e.target.value)}>{state.categories.map(c=><option key={c}>{c}</option>)}</select></label>
          <label className="text-sm font-medium">Tagi · maks. 8, oddziel przecinkami<input className={inputClass} value={tags} disabled={blocked} onChange={e=>setTags(e.target.value)}/></label>
          <label className="text-sm font-medium">Autor · identyfikator w WordPressie<input type="number" min="1" placeholder="Domyślny autor WordPress" className={inputClass} value={author} disabled={blocked} onChange={e=>setAuthor(e.target.value)}/></label>
          <label className="text-sm font-medium">Typ danych strukturalnych<select className={inputClass} value={schema} disabled={blocked} onChange={e=>setSchema(e.target.value)}>{["Article","NewsArticle","TechArticle","HowTo","FAQPage"].map(s=><option key={s}>{s}</option>)}</select></label>
          <label className="text-sm font-medium sm:col-span-2">Adres obrazu wyróżniającego · opcjonalnie<input type="url" className={inputClass} value={image} disabled={blocked} onChange={e=>setImage(e.target.value)}/></label>
        </div>
        {blocked&&!active&&<p className="text-xs text-muted-foreground">Pola odblokują się, gdy wersja będzie zatwierdzona z aktualnym, zaliczonym QA.</p>}
      </ResultBlock>

      <ResultBlock id="wp-seo" icon={SearchIcon} title="Podgląd i dane SEO"
        description="Jak wpis będzie wyglądał w wyszukiwarce i w mediach społecznościowych oraz jakie dane dostanie wtyczka SEO.">
        <div aria-label="Podgląd w wyszukiwarce" className="space-y-1 rounded-xl bg-background p-5 ring-1 ring-foreground/8"><p className="text-xs text-muted-foreground">Podgląd w wyszukiwarce</p><p className="break-all pt-2 text-xs text-emerald-800">{state.profile.canonical_url??`…/${state.profile.slug}/`}</p><p className="text-lg leading-snug text-sky-800">{state.profile.seo_title||"Tytuł SEO wymaga przygotowania"}</p><p className="text-sm leading-6 text-muted-foreground">{state.profile.meta_description}</p></div>
        <dl className="divide-y rounded-xl bg-muted/40 px-4 text-sm">{[["Adres kanoniczny",state.profile.canonical_url??"Po utworzeniu wpisu"],["Główna fraza kluczowa",state.profile.focus_keyword||"—"],["Dodatkowe frazy",state.profile.secondary_keywords.join(", ")||"—"],["Zajawka (excerpt)",state.profile.excerpt],["Tytuł w social media (OG)",state.profile.og_title],["Opis w social media (OG)",state.profile.og_description],["Tytuł na X/Twitterze",state.profile.twitter_title],["Opis na X/Twitterze",state.profile.twitter_description],["Indeksowanie",`${state.profile.robots_index?"index":"noindex"}, ${state.profile.robots_follow?"follow":"nofollow"}`]].map(([label,value])=><div key={label} className="grid gap-1 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4"><dt className="font-medium text-muted-foreground">{label}</dt><dd className="break-words">{value||"—"}</dd></div>)}</dl>
      </ResultBlock>

      <ResultBlock id="wp-checks" icon={ListChecksIcon} title="Wymagania publikacji" count={problemChecks}
        description="Co sprawdzamy przed wysyłką i gdzie to poprawić. „Blokuje” zatrzymuje wysyłkę; „Zalecenie” jej nie blokuje.">
        {state.checks.length===0&&<p className="rounded-lg bg-muted/40 p-4 text-sm text-muted-foreground">Wymagania zostaną sprawdzone, gdy ta wersja będzie zatwierdzona z aktualnym, zaliczonym QA.</p>}
        {state.checks.some(c=>c.status!=="ok")&&<ul className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">{state.checks.filter(c=>c.status!=="ok").map(c=>{
          const st=checkStates[c.status]??{label:c.status,className:"text-muted-foreground"};
          const fix=checkFix(c.name,c.status,state.profile);
          return <li key={c.name} className="space-y-2 bg-background px-4 py-3 text-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3"><span className="font-medium">{labels[c.name]??c.name}{c.value!==undefined&&c.value!==null?` · ${c.value}`:""}</span><span className={`shrink-0 text-xs font-semibold ${st.className}`}>{c.status==="warning"?"Zalecenie":st.label}</span></div>
            {fix.current&&<p className="break-words rounded-md bg-muted/50 px-3 py-2 text-muted-foreground">„{fix.current}”</p>}
            <p className="text-muted-foreground">{fix.text}</p>
            {fix.action&&<Button size="sm" variant="outline" disabled={fix.action.disabled} onClick={fix.action.run}>{fix.action.label}</Button>}
          </li>;})}</ul>}
        {okChecks>0&&<details className="rounded-xl bg-muted/40 px-4 py-3 text-sm"><summary className="cursor-pointer font-medium">Spełnione ({okChecks})</summary>
          <ul className="mt-2 grid gap-1 sm:grid-cols-2">{state.checks.filter(c=>c.status==="ok").map(c=><li key={c.name} className="flex items-center gap-2 text-muted-foreground"><CheckIcon className="size-3.5 text-emerald-600" aria-hidden="true" />{labels[c.name]??c.name}{c.value!==undefined&&c.value!==null?` · ${c.value}`:""}</li>)}</ul></details>}
        <p className="text-xs text-muted-foreground">Wpis w koszu pozostaje bez zmian. Ponowne wysłanie utworzy nowy szkic, także po trwałym usunięciu.</p>
      </ResultBlock>
    </>}
    </div>
  </WorkflowSection>;
}
