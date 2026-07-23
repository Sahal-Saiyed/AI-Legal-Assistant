import { motion } from "framer-motion";
import { memo } from "react";

import { MessageBubble } from "@/components/chat/message-bubble";
import { MessageTimestamp } from "@/components/chat/message-timestamp";

interface UserMessageProps {
  message: string;
  timestamp: string;
}

export const UserMessage = memo(function UserMessage({ message, timestamp }: UserMessageProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-end gap-2"
      aria-label="Your message"
    >
      <MessageBubble variant="user">{message}</MessageBubble>
      <MessageTimestamp value={timestamp} className="mr-2" />
    </motion.article>
  );
});
