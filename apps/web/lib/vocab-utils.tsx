import React from "react";

/**
 * Clean any raw HTML or fill-in-the-blank spans from example sentences.
 * Ensures that sentences are always pure text and safe for display and TTS audio playback.
 */
export function cleanSentence(sentence?: string | null, targetWord?: string): string {
  if (!sentence) return "";
  let clean = sentence.replace(/<span\s+class=['"]blank['"]>______\s*<\/span>/gi, targetWord || "______");
  clean = clean.replace(/<span[^>]*>.*?<\/span>/gi, targetWord || "");
  clean = clean.replace(/<[^>]+>/g, "");
  return clean.trim();
}

export function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Render example sentence with the target vocabulary word highlighted in bold accent color.
 */
export function renderHighlightedSentence(sentence?: string | null, targetWord?: string): React.ReactNode {
  const cleaned = cleanSentence(sentence, targetWord);
  if (!cleaned) return null;
  const word = targetWord?.trim();
  if (!word) return cleaned;

  const escaped = escapeRegExp(word);
  const regex = new RegExp(`(\\b${escaped}\\w*\\b)`, "gi");
  const parts = cleaned.split(regex);
  if (parts.length <= 1) return cleaned;

  return parts.map((part, i) =>
    regex.test(part) ? (
      <strong key={i} className="font-bold text-blue-600 dark:text-blue-400 not-italic">
        {part}
      </strong>
    ) : (
      part
    )
  );
}
