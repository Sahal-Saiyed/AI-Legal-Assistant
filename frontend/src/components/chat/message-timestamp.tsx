import { cn } from "@/lib/utils";

interface MessageTimestampProps {
  value: string;
  className?: string;
}

export function MessageTimestamp({ value, className }: MessageTimestampProps) {
  return (
    <time className={cn("text-[10px] font-medium text-slate-400", className)}>
      {value}
    </time>
  );
}
