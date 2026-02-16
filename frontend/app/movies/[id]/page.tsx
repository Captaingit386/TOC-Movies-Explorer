"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.trim() || "http://127.0.0.1:8000";

type Movie = {
  title: string;
  url: string;
  director?: string;
  release_date?: string;
  running_time?: string;
  country?: string;
  language?: string;
  budget?: string;
  box_office?: string;
};

export default function MovieDetailPage() {
  const params = useParams();
  const id = Array.isArray((params as any)?.id) ? (params as any).id[0] : (params as any)?.id;

  const router = useRouter();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    async function load() {
      setErr(null);
      setMovie(null);

      try {
        const res = await fetch(`${API_BASE}/movies/${id}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();

        setMovie(data); // change if your API wraps the object
      } catch (e: any) {
        setErr(e?.message || "Failed to load");
      }
    }

    load();
  }, [id]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <button
          onClick={() => router.push("/")}
          className="rounded-xl bg-white/5 px-4 py-2 text-sm text-zinc-200 ring-1 ring-white/10 hover:bg-white/10"
        >
          ← Back
        </button>

        {err ? (
          <div className="mt-6 rounded-2xl bg-white/5 p-6 ring-1 ring-white/10">
            <div className="font-semibold text-red-300">Error</div>
            <div className="mt-2 text-sm text-zinc-400">{err}</div>
          </div>
        ) : !movie ? (
          <div className="mt-6 text-zinc-400">Loading…</div>
        ) : (
          <div className="mt-6 overflow-hidden rounded-2xl bg-white/5 ring-1 ring-white/10">
            <div className="border-b border-white/10 p-6">
              <div className="text-sm text-zinc-400">Movie</div>
              <h1 className="mt-1 text-3xl font-semibold">{movie.title}</h1>

              <a
                href={movie.url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-fuchsia-500/20 to-cyan-400/20 px-3 py-1 text-sm ring-1 ring-white/10 hover:ring-white/20"
              >
                Open on Wikipedia ↗
              </a>
            </div>

            <div className="grid gap-4 p-6 sm:grid-cols-2">
              <Info label="Director" value={movie.director} />
              <Info label="Release date" value={movie.release_date} />
              <Info label="Runtime" value={movie.running_time ? `${movie.running_time} minutes` : "—"} />
              <Info label="Country" value={movie.country} />
              <Info label="Language" value={movie.language} />
              <Info label="Budget" value={movie.budget} />
              <Info label="Box office" value={movie.box_office} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-2xl bg-zinc-950/40 p-4 ring-1 ring-white/10">
      <div className="text-xs text-zinc-400">{label}</div>
      <div className="mt-1 text-zinc-100">{value?.trim() || "-"}</div>
    </div>
  );
}
