// frontend/app/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.trim() || "http://127.0.0.1:8000";
const GITHUB_REPO =
  process.env.NEXT_PUBLIC_GITHUB_REPO?.trim() ||
  "https://github.com/Captaingit386/TOC-Movies-Explorer";

type Movie = {
  title: string;
  url: string;
  director?: string;
  release_date?: string;
  running_time?: string | number;
  country?: string;
  language?: string;
  budget?: string;
  box_office?: string;
};

export default function HomePage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const limit = 15;

  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / limit)),
    [total]
  );

  async function load(p: number, query: string) {
    setLoading(true);
    setErr(null);
    try {
      const url = new URL(`${API_BASE}/movies`);
      url.searchParams.set("page", String(p));
      url.searchParams.set("limit", String(limit));
      if (query.trim()) url.searchParams.set("q", query.trim());

      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      setItems(Array.isArray(data.items) ? data.items : []);
      setTotal(typeof data.total === "number" ? data.total : 0);
    } catch (e: any) {
      setErr(e?.message || "Something went wrong");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(page, q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  function onSearch() {
    setPage(1);
    load(1, q);
  }

  return (
    <>
      <div className="posterWall" aria-hidden="true" />
      <div className="glow" aria-hidden="true" />

      <div className="container">
        <div className="topbar">
          <div className="brand">
            <div className="brandMark" />
            <div className="brandName">TOC Movies Explorer</div>
          </div>

          <div className="topActions">
            <a
              className="linkPill"
              href={GITHUB_REPO}
              target="_blank"
              rel="noreferrer"
            >
              GitHub ↗
            </a>
          </div>
        </div>

        <section className="heroBanner">
          <div className="heroInner">
            <h1 className="heroTitle">Movies dataset from Wikipedia</h1>
            <p className="heroDesc">
              We crawl Wikipedia film pages and extract structured fields using
              Python regular expressions (director, release date, runtime,
              country, language, budget, box office). Browse and search over
              100+ movies.
            </p>

            <div className="badges">
              <span className="badge">✅ 120+ movies</span>
              <span className="badge">🐍 FastAPI + Regex</span>
              <span className="badge">⚛️ Next.js UI</span>
            </div>

            <div className="searchRow">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSearch();
                }}
                placeholder="Search title, director, release, runtime, box office..."
                className="input"
              />
              <button onClick={onSearch} className="btn" disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </button>
            </div>
            <div className="searchHelp">
            <div>
              Examples:
              <span className="ex">
                title:Hulk director:John... release:2003
              </span>
            </div>
            <div>
              Filters:
              <span className="ex">
                runtime&gt;=100 boxoffice&gt;100M 
              </span>
            </div>
          </div>

            <div className="metaRow">
              <div>
                Total: <b>{total}</b> movies
              </div>

              <div className="pager">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || loading}
                  className="pagerBtn"
                >
                  Prev
                </button>

                <span className="pill">
                  Page {page} / {totalPages} • {limit}/page
                </span>

                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || loading}
                  className="pagerBtn"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </section>

        <div className="sectionTitle">Browse results</div>

        <div className="card">
          {err ? (
            <div className="pad">
              <div className="errTitle">Something went wrong</div>
              <div className="small">{err}</div>
            </div>
          ) : loading ? (
            <div className="pad small">Loading…</div>
          ) : items.length === 0 ? (
            <div className="pad small">No results. Try another keyword.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Director</th>
                  <th>Release</th>
                  <th>Runtime</th>
                  <th>Box Office</th>
                </tr>
              </thead>

              <tbody>
                {items.map((m, idx) => (
                  <tr key={`${m.url}-${idx}`}>
                    <td>
                      <a
                        className="titleLink"
                        href={m.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {m.title}
                      </a>

                      <div className="k">
                        <span className="tag">{m.country || "-"}</span>
                        <span className="tag">{m.language || "-"}</span>
                      </div>
                    </td>

                    <td className="muted">{m.director || "-"}</td>
                    <td className="muted">{m.release_date || "-"}</td>
                    <td className="muted">
                      {m.running_time ? `${m.running_time} min` : "-"}
                    </td>
                    <td className="muted">{m.box_office || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="footer">Built with FastAPI + Regex + Next.js</div>
      </div>
    </>
  );
}