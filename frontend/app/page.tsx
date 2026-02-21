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
  box_office_usd?: number | null;
};

type ApiResponse = {
  total: number;
  items: Movie[];
};

type StatsResponse = {
  total_movies: number;
  quality: {
    director_pct: number;
    runtime_pct: number;
    release_pct: number;
    boxoffice_pct: number;
    missing_fields_total: number;
  };
  charts: {
    movies_by_decade: { decade: string; count: number }[];
    runtime_distribution: { bucket: string; count: number }[];
  };
};

type SortKey =
  | ""
  | "release_desc"
  | "release_asc"
  | "runtime_desc"
  | "runtime_asc"
  | "boxoffice_desc"
  | "boxoffice_asc"
  | "title_asc";

function formatBoxOfficeMillion(movie: Movie): string {
  const usd = movie.box_office_usd;
  if (typeof usd === "number" && isFinite(usd) && usd > 0) {
    const million = usd / 1_000_000;
    return `$${million.toFixed(million >= 100 ? 0 : 1)} million`;
  }

  const raw = (movie.box_office || "").toString();
  if (!raw) return "-";

  const s = raw
    .toLowerCase()
    .replace(/,/g, "")
    .replace(/us\$/g, "$")
    .replace(/usd/g, "$");

  const m = s.match(/(\d+(?:\.\d+)?)\s*(billion|bn|million|m)\b/);
  if (m) {
    const num = parseFloat(m[1]);
    const unit = m[2];
    const million = unit === "billion" || unit === "bn" ? num * 1000 : num;
    return `$${million.toFixed(million >= 100 ? 0 : 1)} million`;
  }

  const n = s.match(/\$?\s*(\d{1,12})(?:\.\d+)?/);
  if (n) {
    const val = parseFloat(n[1]);
    if (isFinite(val) && val > 0) {
      const million = val / 1_000_000;
      return `$${million.toFixed(million >= 100 ? 0 : 1)} million`;
    }
  }

  return "-";
}

function clampPct(n: number): number {
  if (!isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

function maxCount(arr: { count: number }[]): number {
  let m = 1;
  for (const x of arr) {
    if (typeof x.count === "number" && x.count > m) m = x.count;
  }
  return m;
}

export default function HomePage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const limit = 15;

  const [sort, setSort] = useState<SortKey>("");
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const statCardStyle: React.CSSProperties = {
    padding: 14,
    minWidth: 0,
    height: 104,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  };
  
  const statLabelStyle: React.CSSProperties = {
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  };
  
  const statValueStyle: React.CSSProperties = {
    fontSize: 28,
    fontWeight: 800,
    lineHeight: 1,
  };

  // Dashboard states (does NOT affect search)
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statsErr, setStatsErr] = useState<string | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Collapsible dashboard
  const [showDashboard, setShowDashboard] = useState(false);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / limit)),
    [total]
  );

  async function load(p: number, query: string, sortKey: SortKey) {
    setLoading(true);
    setErr(null);

    try {
      const url = new URL(`${API_BASE}/movies`);
      url.searchParams.set("page", String(p));
      url.searchParams.set("limit", String(limit));
      if (query.trim()) url.searchParams.set("q", query.trim());
      if (sortKey) url.searchParams.set("sort", sortKey);

      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const data: ApiResponse = await res.json();
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

  // IMPORTANT: reload when page OR sort changes (unchanged behavior)
  useEffect(() => {
    load(page, q, sort);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sort]);

  // Fetch stats ONCE (independent of search)
  useEffect(() => {
    let cancelled = false;
    setStatsLoading(true);
    setStatsErr(null);

    fetch(`${API_BASE}/stats`)
      .then((r) => {
        if (!r.ok) throw new Error(`Stats error: ${r.status}`);
        return r.json();
      })
      .then((data: StatsResponse) => {
        if (!cancelled) setStats(data);
      })
      .catch((e: any) => {
        if (!cancelled) setStatsErr(e?.message || "Failed to load stats");
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function onSearch() {
    setPage(1);
    load(1, q, sort);
  }

  function onExportCSV() {
    const url = new URL(`${API_BASE}/export.csv`);
    if (q.trim()) url.searchParams.set("q", q.trim());
    if (sort) url.searchParams.set("sort", sort);
  
    // triggers file download
    window.location.href = url.toString();
  }

  function applyChip(text: string) {
    setQ((prev) => {
      const next = prev.trim() ? `${prev.trim()} ${text}` : text;
      return next;
    });
    setPage(1);
    setTimeout(() => load(1, (q.trim() ? `${q.trim()} ${text}` : text), sort), 0);
  }

  function onClear() {
    setQ("");
    setSort("");
    setPage(1);
    load(1, "", "");
  }

  const decadeMax = useMemo(
    () => (stats ? maxCount(stats.charts.movies_by_decade) : 1),
    [stats]
  );

  const runtimeMax = useMemo(
    () => (stats ? maxCount(stats.charts.runtime_distribution) : 1),
    [stats]
  );

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
              Python regular expressions. Browse and search over 100+ movies.
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
                placeholder='Try: title:Hulk director:"James Cameron" release:2003 runtime>=120 boxoffice>100M'
                className="input"
              />

              <select
                className="sortSelect"
                value={sort}
                onChange={(e) => {
                  const v = e.target.value as SortKey;
                  setSort(v);
                  setPage(1);
                }}
                disabled={loading}
              >
                <option value="">Default</option>
                <option value="release_desc">Release (Newest)</option>
                <option value="release_asc">Release (Oldest)</option>
                <option value="runtime_desc">Runtime (Longest)</option>
                <option value="runtime_asc">Runtime (Shortest)</option>
                <option value="boxoffice_desc">Box Office (Highest)</option>
                <option value="boxoffice_asc">Box Office (Lowest)</option>
                <option value="title_asc">Title (A–Z)</option>
              </select>

              <button onClick={onSearch} className="btn" disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </button>
              <button onClick={onExportCSV} className="btn" disabled={loading}>
                Export CSV
              </button>
            </div>

            <div className="chipRow">
              <button
                className="chip"
                onClick={() => applyChip("runtime>=120")}
                disabled={loading}
              >
                runtime&gt;=120
              </button>
              <button
                className="chip"
                onClick={() => applyChip("boxoffice>100M")}
                disabled={loading}
              >
                boxoffice&gt;100M
              </button>
              <button
                className="chip"
                onClick={() => applyChip("release:2003")}
                disabled={loading}
              >
                release:2003
              </button>
              <button
                className="chip chipClear"
                onClick={onClear}
                disabled={loading}
              >
                Clear
              </button>
            </div>

            <div className="searchHelp">
              <div>
                Examples:
                <span className="ex">title:Hulk director:John release:2003</span>
              </div>
              <div>
                Filters:
                <span className="ex">runtime&gt;=100 boxoffice&gt;100M</span>
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
                  Page {page} / {totalPages}
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

        {/* Collapsible dashboard header */}
        <div style={{ marginTop: 18, marginBottom: 12 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div className="sectionTitle">Dataset dashboard</div>

            <button
              className="chip"
              onClick={() => setShowDashboard((v) => !v)}
              disabled={statsLoading}
            >
              {showDashboard ? "Hide" : "Show"}
            </button>
          </div>

          {showDashboard && (
            <div style={{ marginTop: 10 }}>
              {/* Cards */}
              <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
                    gap: 12,
                  }}
                >
                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Total movies</div>
                  <div style={statValueStyle}>{stats ? stats.total_movies : "—"}</div>
                </div>

                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Director filled</div>
                  <div style={statValueStyle}>
                    {stats ? `${clampPct(stats.quality.director_pct)}%` : "—"}
                  </div>
                </div>

                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Runtime filled</div>
                  <div style={statValueStyle}>
                    {stats ? `${clampPct(stats.quality.runtime_pct)}%` : "—"}
                  </div>
                </div>

                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Box office filled</div>
                  <div style={statValueStyle}>
                    {stats ? `${clampPct(stats.quality.boxoffice_pct)}%` : "—"}
                  </div>
                </div>

                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Release filled</div>
                  <div style={statValueStyle}>
                    {stats ? `${clampPct(stats.quality.release_pct)}%` : "—"}
                  </div>
                </div>

                <div className="card" style={statCardStyle}>
                  <div className="muted" style={statLabelStyle}>Missing fields (total)</div>
                  <div style={statValueStyle}>
                    {stats ? stats.quality.missing_fields_total : "—"}
                  </div>
                </div>
              </div>

              {/* Charts */}
              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  {/* Movies by decade */}
                  <div
                    className="card"
                    style={{ padding: 14, flex: "1 1 420px" }}
                  >
                    <div style={{ fontWeight: 800, marginBottom: 10 }}>
                      Movies by decade
                    </div>

                    {statsLoading && !stats && (
                      <div className="muted">Loading…</div>
                    )}
                    {statsErr && <div className="muted">{statsErr}</div>}

                    {stats && (
                      <div style={{ display: "grid", gap: 10 }}>
                        {stats.charts.movies_by_decade.length === 0 ? (
                          <div className="muted">No release years available.</div>
                        ) : (
                          stats.charts.movies_by_decade.map((row) => {
                            const w = Math.round((row.count / decadeMax) * 100);
                            return (
                              <div
                                key={row.decade}
                                style={{
                                  display: "grid",
                                  gridTemplateColumns: "84px 1fr 44px",
                                  gap: 10,
                                  alignItems: "center",
                                }}
                              >
                                <div className="muted">{row.decade}</div>
                                <div
                                  style={{
                                    height: 10,
                                    borderRadius: 999,
                                    background: "rgba(255,255,255,0.08)",
                                    overflow: "hidden",
                                  }}
                                >
                                  <div
                                    style={{
                                      width: `${w}%`,
                                      height: "100%",
                                      borderRadius: 999,
                                      background: "rgba(255, 0, 0, 0.6)",
                                    }}
                                  />
                                </div>
                                <div
                                  className="muted"
                                  style={{ textAlign: "right" }}
                                >
                                  {row.count}
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>

                  {/* Runtime distribution */}
                  <div
                    className="card"
                    style={{ padding: 14, flex: "1 1 420px" }}
                  >
                    <div style={{ fontWeight: 800, marginBottom: 10 }}>
                      Runtime distribution
                    </div>

                    {statsLoading && !stats && (
                      <div className="muted">Loading…</div>
                    )}
                    {statsErr && <div className="muted">{statsErr}</div>}

                    {stats && (
                      <div style={{ display: "grid", gap: 10 }}>
                        {stats.charts.runtime_distribution.length === 0 ? (
                          <div className="muted">No runtime values available.</div>
                        ) : (
                          stats.charts.runtime_distribution.map((row) => {
                            const w = Math.round((row.count / runtimeMax) * 100);
                            return (
                              <div
                                key={row.bucket}
                                style={{
                                  display: "grid",
                                  gridTemplateColumns: "84px 1fr 44px",
                                  gap: 10,
                                  alignItems: "center",
                                }}
                              >
                                <div className="muted">{row.bucket}</div>
                                <div
                                  style={{
                                    height: 10,
                                    borderRadius: 999,
                                    background: "rgba(255,255,255,0.08)",
                                    overflow: "hidden",
                                  }}
                                >
                                  <div
                                    style={{
                                      width: `${w}%`,
                                      height: "100%",
                                      borderRadius: 999,
                                      background: "rgba(255, 0, 0, 0.6)",
                                    }}
                                  />
                                </div>
                                <div
                                  className="muted"
                                  style={{ textAlign: "right" }}
                                >
                                  {row.count}
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="muted" style={{ marginTop: 10 }}>
                Dashboard is computed from the full dataset (not filtered by search).
              </div>
            </div>
          )}
        </div>

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
                    <td className="muted">{formatBoxOfficeMillion(m)}</td>
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