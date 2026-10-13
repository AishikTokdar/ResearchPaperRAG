/** Incremental SSE framing, including split CRLF and final unterminated frames. */
export async function* readServerEvents(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";
  let data: string[] = [];
  const lineEvent = (line: string) => {
    if (line === "") {
      if (!data.length) { event = "message"; return null; }
      const value = { event, data: JSON.parse(data.join("\n")) };
      event = "message"; data = [];
      return value;
    }
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    return null;
  };
  try {
    for (;;) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let newline;
      while ((newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline).replace(/\r$/, "");
        buffer = buffer.slice(newline + 1);
        const parsed = lineEvent(line);
        if (parsed) yield parsed;
      }
      if (done) {
        if (buffer) lineEvent(buffer.replace(/\r$/, ""));
        const last = lineEvent("");
        if (last) yield last;
        break;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
