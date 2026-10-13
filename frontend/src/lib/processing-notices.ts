/** Hide internal orchestration notices while preserving source limitations and errors. */
export function stripProcessingNotices(text: string): string {
  return text.split(/\r?\n[ \t]*\r?\n/).filter((paragraph) => {
    const plain = paragraph.replace(/^[ \t]*>[ \t]*/gm, "").trim().replace(/^[*_`]+/, "");
    return !/^\[(?:NOTICE|FALLBACK ALERT|PROVIDER API KEY WARNING|API KEY WARNING)\]/i.test(plain)
      && !/^(?:Large context detected\b|Prompt was automatically split\b)/i.test(plain);
  }).join("\n\n").trim();
}
