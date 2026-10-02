"use client";

import Link from "next/link";
import { CheckIcon, SparklesIcon, XIcon } from "lucide-react";

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
    <div className="overflow-x-auto rounded-xl bg-card ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16 pl-4">Score</TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Published</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="pr-4 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {candidates.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                No candidates. Add an RSS source and click “Fetch all”.
              </TableCell>
            </TableRow>
          )}
          {candidates.map((candidate) => {
            const busy = busyId === candidate.id;
            return (
              <TableRow key={candidate.id} className={candidate.status === "ignored" ? "opacity-60" : ""}>
                <TableCell className="pl-4">
                  <ScoreBadge score={candidate.total_score} />
                </TableCell>
                <TableCell className="max-w-[28rem] whitespace-normal">
                  <Link
                    href={`/candidates/${candidate.id}`}
                    className="line-clamp-2 font-medium hover:underline"
                  >
                    {candidate.title}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{candidate.source_name}</TableCell>
                <TableCell>
                  <CategoryBadge category={candidate.category} />
                </TableCell>
                <TableCell
                  className="text-muted-foreground"
                  title={formatDate(candidate.original_published_at)}
                >
                  {timeAgo(candidate.original_published_at)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={candidate.status} />
                </TableCell>
                <TableCell className="pr-4">
                  <div className="flex justify-end gap-1">
                    {candidate.total_score === null && (
                      <Button
                        size="icon-sm"
                        variant="outline"
                        title="Classify"
                        aria-label="Classify"
                        disabled={busy}
                        onClick={() => onClassify(candidate)}
                      >
                        <SparklesIcon />
                      </Button>
                    )}
                    <Button
                      size="icon-sm"
                      variant="outline"
                      title="Approve"
                      aria-label="Approve"
                      disabled={busy || candidate.status === "approved"}
                      onClick={() => onStatusChange(candidate, "approved")}
                    >
                      <CheckIcon />
                    </Button>
                    <Button
                      size="icon-sm"
                      variant="outline"
                      title="Ignore"
                      aria-label="Ignore"
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
