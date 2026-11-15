"use client";

import Link from "next/link";
import { CheckIcon, InboxIcon, SparklesIcon, XIcon } from "lucide-react";

import { CategoryBadge, StatusBadge } from "@/components/status-badge";
import { ScoreBadge } from "@/components/score-badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate, timeAgo } from "@/lib/format";
import type { Candidate, CandidateStatus } from "@/types/api";

interface CandidatesTableProps {
  candidates: Candidate[];
  busyId: number | null;
  onStatusChange: (candidate: Candidate, status: CandidateStatus) => void;
  onClassify: (candidate: Candidate) => void;
}

export function CandidatesTable({ candidates, busyId, onStatusChange, onClassify }: CandidatesTableProps) {
  return (
    <div className="min-w-0 overflow-x-auto">
      <Table aria-label="Lista tematów">
        <TableHeader>
          <TableRow className="bg-muted/40 hover:bg-muted/40 [&>th]:h-10 [&>th]:text-xs [&>th]:font-medium [&>th]:uppercase [&>th]:tracking-wider [&>th]:text-muted-foreground">
            <TableHead scope="col" className="w-16 pl-4 sm:pl-5">Wynik</TableHead>
            <TableHead scope="col">Temat</TableHead>
            <TableHead scope="col" className="hidden md:table-cell">Źródło</TableHead>
            <TableHead scope="col" className="hidden md:table-cell">Kategoria</TableHead>
            <TableHead scope="col" className="hidden md:table-cell">Publikacja</TableHead>
            <TableHead scope="col">Status</TableHead>
            <TableHead scope="col" className="pr-4 text-right sm:pr-5">Akcje</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {candidates.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="py-16 text-center whitespace-normal">
                <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground" aria-hidden="true"><InboxIcon className="size-6" /></span>
                <p className="text-muted-foreground">Brak tematów. Dodaj źródło RSS i wybierz „Pobierz RSS”.</p>
                <Link href="/sources" className="mt-3 inline-block text-sm font-medium text-emerald-800 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">Zarządzaj źródłami</Link>
              </TableCell>
            </TableRow>
          )}
          {candidates.map((candidate) => {
            const busy = busyId === candidate.id;
            return (
              <TableRow key={candidate.id} className={candidate.status === "ignored" ? "opacity-60" : ""}>
                <TableCell className="py-3 pl-4 sm:pl-5">
                  <ScoreBadge score={candidate.total_score} />
                </TableCell>
                <TableCell className="min-w-48 max-w-[28rem] whitespace-normal">
                  <Link
                    href={`/candidates/${candidate.id}`}
                    className="line-clamp-2 font-medium text-foreground decoration-emerald-600/40 underline-offset-4 hover:text-emerald-800 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    {candidate.title}
                  </Link>
                  <span className="mt-1 block text-xs text-muted-foreground md:hidden">{candidate.source_name} · {timeAgo(candidate.original_published_at)}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-1.5 empty:hidden">
                  {(candidate.group_size ?? 1) > 1 && <span className="inline-block rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-800 ring-1 ring-sky-200" title="Ten sam temat z kilku kanałów RSS">+{(candidate.group_size ?? 1) - 1} {(candidate.group_size ?? 1) - 1 === 1 ? "źródło" : "źródła"}</span>}
                  {candidate.topic_group_id && <span className="inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">duplikat #{candidate.topic_group_id}</span>}
                  </span>
                </TableCell>
                <TableCell className="hidden text-muted-foreground md:table-cell">{candidate.source_name}</TableCell>
                <TableCell className="hidden md:table-cell">
                  <CategoryBadge category={candidate.category} />
                </TableCell>
                <TableCell
                  className="hidden text-muted-foreground md:table-cell"
                  title={formatDate(candidate.original_published_at)}
                >
                  {timeAgo(candidate.original_published_at)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={candidate.workflow_status ?? candidate.status} />
                  <span className={`mt-1 block text-xs ${candidate.total_score === null ? "text-amber-700" : "text-muted-foreground"}`}>{candidate.total_score === null ? "AI: do oceny" : "AI: oceniono"}</span>
                </TableCell>
                <TableCell className="pr-4 sm:pr-5">
                  <div className="flex justify-end gap-1">
                    {candidate.total_score === null && (
                      <Button
                        size="sm"
                        variant="outline"
                        title="Oceń temat · płatne wywołanie AI"
                        aria-label={`Oceń temat · płatne wywołanie AI: ${candidate.title}`}
                        disabled={busy}
                        onClick={() => onClassify(candidate)}
                      >
                        <SparklesIcon /> Oceń · płatne
                      </Button>
                    )}
                    <Button
                      size="icon-sm"
                      variant="outline"
                      title="Zatwierdź temat"
                      aria-label={`Zatwierdź temat: ${candidate.title}`}
                      disabled={busy || candidate.status === "approved"}
                      onClick={() => onStatusChange(candidate, "approved")}
                    >
                      <CheckIcon />
                    </Button>
                    <Button
                      size="icon-sm"
                      variant="outline"
                      title="Pomiń temat"
                      aria-label={`Pomiń temat: ${candidate.title}`}
                      disabled={busy || candidate.status === "ignored"}
                      onClick={() => onStatusChange(candidate, "ignored")}
                    >
                      <XIcon />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
