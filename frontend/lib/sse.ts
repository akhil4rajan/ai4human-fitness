/** Parse a Server-Sent Events byte stream into JSON payloads. Handles events split
 *  across chunks and CRLF line endings. (EventSource can't POST, so we parse by hand.) */
export async function* parseSSE<T>(body: ReadableStream<Uint8Array>): AsyncGenerator<T> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const data = raw
          .split("\n")
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).replace(/^ /, ""))
          .join("\n");
        if (data) yield JSON.parse(data) as T;
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}
