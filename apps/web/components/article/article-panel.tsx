"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRightIcon, ClipboardListIcon, FileTextIcon, LinkIcon, MessageSquareQuoteIcon, RefreshCwIcon, SearchIcon, ShieldCheckIcon, SparklesIcon } from "lucide-react";
import { ResultBlock, setResultBlock } from "@/components/stage/result-block";
import { toast } from "sonner";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { navigateStage } from "@/components/pipeline-state";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { articleState } from "@/lib/workflow";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import type {
  Article,
  ArticleSummary,
  ArticleUpdate,
  CandidateCategory,
  CoveredBy,
  GenerateArticleRequest,
  Research,
} from "@/types/api";

import { WordPressPanel } from "./wordpress-panel";
import { QAPanel } from "./qa-panel";
import { ArticleWorkspace } from "./article-workspace";
import { FeedbackPanel } from "./feedback-panel";
import { GenerateArticleDialog } from "./generate-article-dialog";
import { VersionBar } from "./version-bar";

interface ArticlePanelProps {
  candidateId: number;
  candidateCategory: CandidateCategory | null;
  research: Research | null;
  coveredBy?: CoveredBy | null;
  editorTake?: React.ReactNode;
}

export function ArticlePanel({ candidateId, research, coveredBy = null, editorTake }: ArticlePanelProps) {
  const demo = useDemoMode();
  const selectedId = useRef<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [versions, setVersions] = useState<ArticleSummary[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [dialog, setDialog] = useState<"generate" | "regenerate" | null>(null);
  const [generating, setGenerating] = useState(false);
  const [editing, setEditing] = useState(false);
  // Formularz i docelowy ID są zamrożone na czas edycji tej konkretnej wersji.
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [saving, setSaving] = useState(false);
  const [selectingVersion, setSelectingVersion] = useState(false);

  const loadVersions = useCallback(
    async (selectId?: number, expectedId?: number) => {
      try {
        const list = await api.listArticles(candidateId);
        setVersions(list);
        const target = selectId ?? list.find((v) => v.is_current)?.id ?? list[0]?.id;
        const next = target ? await api.getArticle(target) : null;
        if (expectedId !== undefined && selectedId.current !== expectedId) return true;
        selectedId.current = next?.id ?? null;
        setArticle(next);
        setLoadError(null);
        setLoaded(true);
        return true;
      } catch (error) {
        setLoadError(errorText(error));
        toast.error("Nie udało się wczytać artykułów", { description: errorText(error) });
        return false;
      }
    },
    [candidateId],
  );

  async function selectVersion(id: number) {
    if (editing || selectingVersion) return;
    selectedId.current = id;
    setSelectingVersion(true);
    try { await loadVersions(id); }
    finally { setSelectingVersion(false); }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void loadVersions();
  }, [loadVersions]);

  const jobs = useCandidateJobs(candidateId, "write", loadVersions);
  const generationBusy = generating || Boolean(jobs.active) || !jobs.loaded;

  const researchReady = research?.status === "completed" && research.facts.length > 0;
  const generationHasRun = versions.length > 0 || jobs.history.length > 0;

  async function generate(options: GenerateArticleRequest) {
    setGenerating(true);
    setGenerationError(null);
    try {
      await jobs.enqueue(() => dialog === "regenerate" && article
        ? api.regenerateArticle(article.id, options)
        : api.generateArticle(candidateId, options));
      toast.success("Generowanie zapisane w kolejce");
      setDialog(null);
      setEditing(false);
    } catch (error) {
      setGenerationError(errorText(error));
      toast.error("Nie udało się wygenerować tekstu", { description: errorText(error) });
    } finally {
      setGenerating(false);
    }
  }

  async function save(data: ArticleUpdate) {
    if (!editingArticle) return;
    const editedId = editingArticle.id;
    if (Object.keys(data).length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await api.updateArticle(editedId, data);
      setArticle(updated);
      setEditing(false);
      toast.success("Zapisano nową wersję · QA wymagane");
      setResultBlock("article-text");
      await loadVersions(updated.id);
    } catch (error) {
      toast.error("Nie udało się zapisać wersji", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  function editArticle(field?: unknown) {
    if (!article || selectingVersion || jobs.active) return;
    const target = typeof field === "string" ? field : null;
    setEditingArticle(article); setEditing(true);
    requestAnimationFrame(() => {
      window.location.hash = "article-workspace";
      window.dispatchEvent(new Event("article-workspace-read"));
      document.getElementById("article-workspace")?.scrollIntoView({block:"start"});
      document.getElementById("article-editor-heading")?.focus({preventScroll:true});
      if (target) setTimeout(() => {
        const input = document.querySelector<HTMLElement>(`#article-workspace [name="${target}"]`);
        input?.scrollIntoView({ block: "center" });
        input?.focus({ preventScroll: true });
      }, 60);
    });
  }

  return (
    <>
    {article && <VersionBar article={article} versions={versions} selecting={selectingVersion} editing={editing} onSelect={selectVersion} />}
    <WorkflowSection progressJob={jobs.ownActive} revealEvent={`article-${article?.id}-reveal`} number={4} title="Generowanie artykułu" description="AI pisze brief i tekst na podstawie bazy faktów z researchu." paid resultTitle={null}
      initiallyCollapsed={loaded ? versions.length > 0 : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : generationError ? "Ostatnie uruchomienie: błąd" : articleState(Boolean(article), generating, Boolean(researchReady), loaded)}
      actionTitle="Generowanie" actionDescription={article ? "Tekst jest gotowy. Przeczytaj wybraną wersję i przekaż ją do QA. Nowa wersja powstanie od zera i naliczy koszt AI." : "Wybierz format, długość i perspektywę. Brief i artykuł powstaną w jednym zadaniu."}
      blocker={!researchReady ? "Ukończ research ze zweryfikowanymi faktami, aby odblokować generowanie." : editing ? "Zapisz lub anuluj edycję przed generowaniem nowej wersji." : undefined}
      primary={<Button variant={generationHasRun ? "outline" : "default"} onClick={() => setDialog(article ? "regenerate" : "generate")} disabled={!researchReady || !loaded || generationBusy || editing || selectingVersion}>
        {generationHasRun ? <RefreshCwIcon /> : <SparklesIcon />}{generationHasRun ? `Nowa wersja · ${demo ? "demo · bezpłatne" : "płatne"}` : `Generuj artykuł · ${demo ? "demo · bezpłatne" : "płatne"}`}
      </Button>}
      navigation={<>
        <Button variant={article ? "default" : "outline"} onClick={() => navigateStage(5)}>Przejdź do QA<ArrowRightIcon /></Button>
        {!article && <p className="action-hint">QA będzie można uruchomić po wygenerowaniu artykułu.</p>}
      </>}
      activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[
        {label: "Brief", configured: "brief", model: article?.brief_llm_model, input: article?.brief_llm_model ? article.brief_input_tokens : null, output: article?.brief_llm_model ? article.brief_output_tokens : null, cost: article?.brief_cost_usd},
        {label: "Pisanie artykułu", configured: "writer", model: article?.llm_model, input: article?.llm_model ? article.writer_input_tokens : null, output: article?.llm_model ? article.writer_output_tokens : null, cost: article?.writer_cost_usd}
      ]} total={article?.estimated_cost_usd} note={demo ? "Generacja demo jest bezpłatna. Każde uruchomienie tworzy nową wersję i zachowuje historię." : "Każda generacja tworzy nową, płatną wersję. Poprzednie wersje pozostają dostępne. Edycja i zmiana statusu nie wywołują AI."} />}>
      {loadError && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{loadError}</p>}
      {generationError && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{generationError} — możesz ponowić generowanie; kolejne wywołanie może naliczyć koszt.</p>}
      {article ? <ArticleWorkspace article={article} versions={versions} selecting={selectingVersion}
        editingArticle={editing ? editingArticle : null} saving={saving} editingBlocked={Boolean(jobs.active)} onSelect={selectVersion}
        onEdit={editArticle} onSave={save} onCancel={() => setEditing(false)}
        extra={<>
          <ResultBlock id="article-editor-take" icon={MessageSquareQuoteIcon} title="Komentarz redakcji"
            description="Opinia redakcji dla kolejnych generacji. Zmiana nie wpływa na istniejące wersje — użyj „Nowa wersja”, aby ją uwzględnić.">{editorTake}</ResultBlock>
          <FeedbackPanel candidateId={candidateId} versions={versions} />
        </>} /> :
        <section tabIndex={-1} id="article-workspace" aria-labelledby="article-empty-title" aria-busy={!loaded && !loadError} className="scroll-mt-56 space-y-7">
          <div className="rounded-xl border border-dashed p-5">
            <h3 id="article-empty-title" className="font-medium">{!loaded ? "Wczytywanie artykułów…" : researchReady ? "Artykuł nie został jeszcze wygenerowany" : "Najpierw ukończ research"}</h3>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{researchReady ? "Po uruchomieniu AI w jednym zadaniu przygotuje:" : "Generowanie korzysta z bazy faktów z researchu. Gdy research się zakończy, AI przygotuje:"}</p>
            <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              {([[ClipboardListIcon, "Brief", "kąt, odbiorców i plan sekcji"], [FileTextIcon, "Tekst", "tytuł, lead i treść w Markdown"], [LinkIcon, "Powiązania", "który fakt stoi za którą częścią"], [SearchIcon, "SEO", "meta title, opis, slug i frazy"]] as const).map(([Icon, title, text]) => (
                <li key={title} className="flex gap-2"><Icon className="mt-0.5 size-4 shrink-0 text-emerald-700" aria-hidden="true" /><span><span className="font-medium">{title}</span> <span className="text-muted-foreground">— {text}</span></span></li>
              ))}
            </ul>
          </div>
          <ResultBlock id="article-editor-take" icon={MessageSquareQuoteIcon} title="Komentarz redakcji"
            description="Opcjonalnie: doświadczenie lub opinia redakcji. Uzupełnij przed generowaniem — AI doda je jako oznaczony komentarz.">{editorTake}</ResultBlock>
        </section>}

      <GenerateArticleDialog
        open={dialog !== null}
        onOpenChange={(open) => !open && setDialog(null)}
        title={dialog === "regenerate" ? `Generuj nową wersję na podstawie v${article?.version}` : "Generuj artykuł"}
        defaults={dialog === "regenerate" && article ? article.generation_options : {}}
        suggestedAngle={research?.suggested_angle ?? null}
        refreshTarget={coveredBy?.post_id ? { title: coveredBy.title, url: coveredBy.url ?? null } : null}
        busy={generationBusy}
        onSubmit={generate}
      />
    </WorkflowSection>
    {!article && <>
      <WorkflowSection number={5} title="Kontrola jakości (QA)" paid status="Najpierw wygeneruj artykuł"
        description="Kontrola faktów i jakości wybranej wersji na podstawie zapisanych dowodów." initiallyCollapsed
        actionTitle="QA" actionDescription="QA ocenia tekst i wskazuje problemy. Poprawki i decyzja są w kolejnym etapie."
        blocker="Wymaga wygenerowanego artykułu."
        primary={<Button disabled><ShieldCheckIcon />Uruchom QA</Button>}
        navigation={<Button variant="outline" onClick={() => navigateStage(6)}>Przejdź do poprawek i zatwierdzenia<ArrowRightIcon /></Button>}
        summary={<UsageSummary note="QA będzie dostępne po wygenerowaniu artykułu." />}>
        <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Brak wersji do sprawdzenia. Ukończ research i wygeneruj artykuł.</p>
      </WorkflowSection>
      <WorkflowSection number={6} title="Poprawki i zatwierdzenie" paid status="Najpierw wykonaj QA"
        description="Poprawki i decyzja redakcyjna zawsze dotyczą wybranej wersji artykułu." initiallyCollapsed
        actionTitle="Poprawki i decyzja" actionDescription="Popraw tekst automatycznie lub ręcznie, a potem zatwierdź albo odrzuć wersję."
        blocker="Wymaga artykułu i aktualnego, zaliczonego QA."
        primaryTitle="Poprawki tekstu"
        primary={<><Button disabled>Popraw automatycznie</Button><Button variant="outline" disabled>Edytuj tekst</Button></>}
        secondaryTitle="Decyzja"
        secondary={<><Button variant="outline" disabled>Zatwierdź wersję</Button><Button variant="outline" disabled>Odrzuć wersję</Button></>}
        navigation={<Button variant="outline" onClick={() => navigateStage(8)}>Przejdź do publikacji<ArrowRightIcon /></Button>}
        summary={<UsageSummary note="Poprawki wymagają ukończonego QA; zatwierdzenie wymaga aktualnego, zaliczonego QA." />}>
        <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Po QA zobaczysz tu propozycje poprawek. Zatwierdzenie będzie dostępne po spełnieniu wymagań jakości.</p>
      </WorkflowSection>
      <WorkflowSection number={8} title="Publikacja w WordPressie" paid={false} status="Najpierw przygotuj artykuł"
        description="Ustawienia publikacji i wysyłka zatwierdzonej wersji do WordPressa."
        actionTitle="Publikacja" actionDescription="Wyślij zatwierdzoną wersję jako szkic, zaplanuj albo opublikuj wpis."
        blocker="Wymaga zatwierdzonej wersji z aktualnym, zaliczonym QA."
        primary={<><Button disabled>Utwórz szkic w WordPressie</Button><Button variant="outline" disabled>Opublikuj teraz</Button></>}
        secondaryTitle="Planowanie"
        secondary={<Button variant="outline" disabled>Zaplanuj publikację</Button>}
        navigationTitle="Koniec procesu"
        navigation={<Link href="/" className={buttonVariants({ variant: "outline" })}>Wróć do listy tematów</Link>}
        summary={<UsageSummary free note="Wysyłka zwykle nie wywołuje AI. Brakujące pola SEO system uzupełnia modelem AI; ten krok nie jest blokowany przez budżet." />}>
        <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Ustawienia publikacji pojawią się po wygenerowaniu artykułu.</p>
      </WorkflowSection>
    </>}
    {article && <QAPanel key={`qa-${article.id}`} article={article} versions={versions} onSelectVersion={selectVersion}
      onVersionCreated={async (id, sourceId) => { if (!editing) await loadVersions(id, sourceId); }}
      onEdit={editArticle}
      selectingVersion={selectingVersion} candidateId={candidateId} editing={editing} onArticleChange={async () => {
      const refreshed = await api.getArticle(article.id);
      // A completed QA read must not select an older version after the user/Write selected another.
      setArticle((current) => current?.id === refreshed.id ? refreshed : current);
      setVersions((current) => current.map((version) => version.id === refreshed.id ? {...version, ...refreshed} : version));
    }} />}
    {article && <WordPressPanel key={`wordpress-${article.id}`} article={article} onSelectVersion={selectVersion} editing={editing} onEdit={editArticle} />}
    </>
  );
}
