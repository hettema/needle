import { useCallback, useEffect, useRef, useState } from "react";
import { getProjects } from "./api";
import type { Project } from "./types/project";
import { AppHead, Notice, Wordmark } from "./components/ui";
import { Board } from "./board/Board";
import { useBoard } from "./state/board";

/**
 * The path is the state: `/p/<slug>` names the project on the page, and the
 * page remembers nothing else, so a reload, a link and the back button all
 * land where they say. Switching projects pushes a path; the browser's own
 * history walks it back.
 */
function slugFromPath(): string | null {
  const match = /^\/p\/([^/]+)/.exec(window.location.pathname);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function BoardPage({ slug, projects, onSwitch, onBoardChange }: { slug: string; projects: Project[]; onSwitch: (slug: string) => void; onBoardChange: () => Promise<void> }) {
  const store = useBoard(slug);
  // A board change is the one signal the page has that the store moved; the
  // project list is re-read on it so a project added while the page is open
  // is in the switcher without a reload.
  const version = store.board?.version;
  const seen = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (version === undefined) return;
    if (seen.current !== undefined && seen.current !== version) void onBoardChange();
    seen.current = version;
  }, [version, onBoardChange]);
  return <Board slug={slug} store={store} projects={projects} onSwitch={onSwitch} />;
}

export function App() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slug, setSlug] = useState<string | null>(slugFromPath);

  const reloadProjects = useCallback(async () => {
    try {
      setProjects(await getProjects());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void reloadProjects();
  }, [reloadProjects]);

  useEffect(() => {
    const onPop = () => setSlug(slugFromPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((next: string) => {
    window.history.pushState(null, "", `/p/${encodeURIComponent(next)}`);
    setSlug(next);
  }, []);

  const current = slug ?? projects?.[0]?.slug ?? null;
  if (current) return <BoardPage key={current} slug={current} projects={projects ?? []} onSwitch={navigate} onBoardChange={reloadProjects} />;
  return (
    <>
      <AppHead>
        <Wordmark />
      </AppHead>
      {error ? <Notice>The board could not be reached: {error}</Notice> : projects ? <Notice>No project is on the board yet. Run <code>uv run needle add /path/to/repo</code> and start the server again.</Notice> : <Notice quiet>Reading…</Notice>}
    </>
  );
}
