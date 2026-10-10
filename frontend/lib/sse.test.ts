import { describe, expect, it } from "vitest";
import { parseSSE } from "./sse";

function stream(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(c) {
      chunks.forEach((x) => c.enqueue(enc.encode(x)));
      c.close();
    },
  });
}

async function collect<T>(s: ReadableStream<Uint8Array>): Promise<T[]> {
  const out: T[] = [];
  for await (const e of parseSSE<T>(s)) out.push(e);
  return out;
}

describe("parseSSE", () => {
  it("parses multiple events in one chunk", async () => {
    const r = await collect(stream(['data: {"a":1}\n\ndata: {"a":2}\n\n']));
    expect(r).toEqual([{ a: 1 }, { a: 2 }]);
  });

  it("reassembles events split across chunks, even mid-multibyte-text", async () => {
    const r = await collect(stream(['data: {"t":"he', 'llo é"}\n', '\ndata: {"t":"x"}\n\n']));
    expect(r).toEqual([{ t: "hello é" }, { t: "x" }]);
  });

  it("handles CRLF endings", async () => {
    const r = await collect(stream(['data: {"a":1}\r\n\r\n']));
    expect(r).toEqual([{ a: 1 }]);
  });

  it("ignores comments and non-data fields", async () => {
    const r = await collect(stream([': keepalive\n\nevent: x\ndata: {"a":1}\n\n']));
    expect(r).toEqual([{ a: 1 }]);
  });

  it("yields nothing for an empty stream", async () => {
    expect(await collect(stream([]))).toEqual([]);
  });
});
