import botIcon from "@/assets/bot_icon.png";
import { cn } from "@/lib/utils";

interface BotAvatarProps {
  className?: string;
}

export function BotAvatar({ className }: BotAvatarProps) {
  return (
    <span
      className={cn(
        "grid size-9 shrink-0 place-items-center overflow-hidden rounded-2xl bg-[#07111d] shadow-sm",
        className,
      )}
      aria-hidden="true"
    >
      <img src={botIcon} alt="" className="size-full object-cover" />
    </span>
  );
}
