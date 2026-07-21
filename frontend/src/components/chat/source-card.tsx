import { FileText } from "lucide-react";

interface SourceCardProps {
  title: string;
  category?: string;
}

export function SourceCard({ title, category }: SourceCardProps) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-2xl border border-[#deebe6] bg-[#f5faf8] p-3.5 transition-colors hover:border-[#c8dfd7] hover:bg-[#edf7f3]">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-white text-[#2c7968] shadow-sm">
        <FileText className="size-4" strokeWidth={1.7} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-semibold text-slate-700">{title}</span>
        {category ? (
          <span className="mt-0.5 block text-[10px] capitalize text-slate-400">
            {category.replaceAll("_", " ")}
          </span>
        ) : null}
      </span>
    </div>
  );
}
