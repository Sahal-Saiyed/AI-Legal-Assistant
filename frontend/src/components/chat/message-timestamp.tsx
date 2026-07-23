import { cn } from "@/lib/utils";

interface MessageTimestampProps {
  value: string;
  className?: string;
}

export function MessageTimestamp({ value, className }: MessageTimestampProps) {
  const date = new Date(value);
  const validDate = !Number.isNaN(date.getTime());
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const sameDay = (left: Date, right: Date) =>
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate();
  const time = validDate
    ? new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date)
    : value;
  const displayValue = !validDate
    ? value
    : sameDay(date, today)
      ? `Today at ${time}`
      : sameDay(date, yesterday)
        ? `Yesterday at ${time}`
        : new Intl.DateTimeFormat(undefined, {
            day: "numeric",
            month: "short",
            year: date.getFullYear() === today.getFullYear() ? undefined : "numeric",
            hour: "numeric",
            minute: "2-digit",
          }).format(date);

  return (
    <time
      dateTime={validDate ? date.toISOString() : undefined}
      title={validDate ? date.toLocaleString() : value}
      className={cn("text-[10px] font-medium text-slate-400", className)}
    >
      {displayValue}
    </time>
  );
}
