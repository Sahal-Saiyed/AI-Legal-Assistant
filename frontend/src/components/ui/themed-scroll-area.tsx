import { useCallback, useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ThemedScrollAreaProps {
  children: ReactNode;
  className?: string;
  viewportClassName?: string;
  variant?: "light" | "dark";
  ariaLive?: "off" | "polite" | "assertive";
}

export function ThemedScrollArea({
  children,
  className,
  viewportClassName,
  variant = "light",
  ariaLive,
}: ThemedScrollAreaProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ pointerId: number; startY: number; startScrollTop: number } | null>(
    null,
  );
  const [thumb, setThumb] = useState({ height: 0, top: 0, visible: false });

  const updateThumb = useCallback(() => {
    const viewport = viewportRef.current;
    const track = trackRef.current;
    if (!viewport || !track) return;
    const { clientHeight, scrollHeight, scrollTop } = viewport;
    const trackHeight = track.clientHeight;
    if (scrollHeight <= clientHeight + 1 || trackHeight <= 0) {
      setThumb({ height: 0, top: 0, visible: false });
      return;
    }
    const height = Math.max(36, (clientHeight / scrollHeight) * trackHeight);
    const availableTravel = trackHeight - height;
    const top = (scrollTop / (scrollHeight - clientHeight)) * availableTravel;
    setThumb({ height, top, visible: true });
  }, []);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    updateThumb();
    const observer = new ResizeObserver(updateThumb);
    observer.observe(viewport);
    if (viewport.firstElementChild) observer.observe(viewport.firstElementChild);
    viewport.addEventListener("scroll", updateThumb, { passive: true });
    return () => {
      observer.disconnect();
      viewport.removeEventListener("scroll", updateThumb);
    };
  }, [children, updateThumb]);

  const startDragging = (event: PointerEvent<HTMLSpanElement>) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startScrollTop: viewport.scrollTop,
    };
  };

  const dragThumb = (event: PointerEvent<HTMLSpanElement>) => {
    const drag = dragRef.current;
    const viewport = viewportRef.current;
    const track = trackRef.current;
    if (!drag || !viewport || !track || drag.pointerId !== event.pointerId) return;
    const availableTravel = track.clientHeight - thumb.height;
    if (availableTravel <= 0) return;
    const scrollRange = viewport.scrollHeight - viewport.clientHeight;
    viewport.scrollTop =
      drag.startScrollTop + ((event.clientY - drag.startY) / availableTravel) * scrollRange;
  };

  const stopDragging = (event: PointerEvent<HTMLSpanElement>) => {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <div className={cn("relative min-h-0", className)}>
      <div
        ref={viewportRef}
        className={cn(
          "scrollbar-hidden h-full overflow-y-auto overscroll-contain",
          viewportClassName,
        )}
        aria-live={ariaLive}
      >
        <div>{children}</div>
      </div>
      <div
        ref={trackRef}
        className={cn(
          "absolute bottom-2 right-1 top-2 w-2 rounded-full transition-opacity duration-200",
          variant === "dark" ? "bg-white/[0.05]" : "bg-[#102c2a]/[0.06]",
          thumb.visible ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
        )}
        aria-hidden="true"
      >
        {thumb.visible ? (
          <span
            className={cn(
              "absolute inset-x-0 cursor-grab touch-none rounded-full shadow-sm transition-[background-color] active:cursor-grabbing",
              variant === "dark" ? "bg-teal-400/55" : "bg-[#102c2a]",
            )}
            style={{ height: thumb.height, transform: `translateY(${thumb.top}px)` }}
            onPointerDown={startDragging}
            onPointerMove={dragThumb}
            onPointerUp={stopDragging}
            onPointerCancel={stopDragging}
          />
        ) : null}
      </div>
    </div>
  );
}
