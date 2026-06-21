import { useState } from "react";
import { ClearApi, ApiError } from "../api";
import type { NlpSeverityResult } from "../types";

const BAND_BG: Record<string, string> = {
  low: "bg-brutal-green",
  medium: "bg-brutal-yellow",
  high: "bg-brutal-orange",
  critical: "bg-brutal-pink",
};

export default function CitizenSeverityCheck() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<NlpSeverityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function check() {
    const q = text.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await ClearApi.nlpSeverity({ text: q }));
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="brutal-card border-[6px] bg-white p-4 flex flex-col gap-3 shrink-0">
      <h2 className="text-2xl font-black uppercase border-b-4 border-black pb-2">
        Check Severity
      </h2>
      <p className="font-bold text-xs">EN / हिंदी / ಕನ್ನಡ</p>
      <textarea
        className="w-full border-4 border-black p-2 font-bold text-sm shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
        rows={2}
        placeholder="e.g. पेड़ गिरा है, रास्ता बंद / heavy waterlogging"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        onClick={check}
        disabled={loading || !text.trim()}
        className="brutal-btn bg-brutal-blue text-white hover:bg-brutal-yellow hover:text-black disabled:opacity-50"
      >
        {loading ? "Checking…" : "Check"}
      </button>

      {error && (
        <p className="font-bold text-sm text-red-600 border-2 border-red-600 p-2">{error}</p>
      )}

      {result && (
        <div
          className={`border-4 border-black p-3 shadow-[4px_4px_0_0_rgba(0,0,0,1)] ${
            BAND_BG[result.band] ?? "bg-white"
          }`}
        >
          <div className="text-2xl font-black uppercase">{result.band}</div>
          <div className="font-bold text-sm">
            confidence: {Math.round(result.confidence * 100)}%
          </div>
          {result.source && result.source !== "precomputed" && (
            <div className="font-bold text-xs mt-1">
              {result.source === "nearest" ? "closest known phrase" : "default estimate"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
