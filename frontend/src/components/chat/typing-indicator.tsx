import { motion } from "framer-motion";
import { Scale } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-3" role="status" aria-label="JuriGPT is preparing a response">
      <span className="hidden size-9 shrink-0 place-items-center rounded-2xl bg-[#dff2ea] text-[#236f5f] sm:grid">
        <Scale className="size-4" strokeWidth={1.8} />
      </span>
      <div className="w-full max-w-[430px] rounded-[24px] rounded-bl-lg bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((dot) => (
            <motion.span
              key={dot}
              className="size-1.5 rounded-full bg-[#4b8b7d]"
              animate={{ y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
              transition={{ duration: 0.9, repeat: Infinity, delay: dot * 0.14 }}
            />
          ))}
          <span className="ml-2 text-[10px] font-medium text-slate-400">Reviewing legal sources</span>
        </div>
        <div className="mt-4 space-y-2.5" aria-hidden="true">
          {["92%", "78%", "56%"].map((width, index) => (
            <motion.div
              key={width}
              className="h-2 rounded-full bg-stone-100"
              style={{ width }}
              animate={{ opacity: [0.45, 0.9, 0.45] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: index * 0.12 }}
            />
          ))}
        </div>
        <span className="sr-only">JuriGPT is typing</span>
      </div>
    </div>
  );
}
