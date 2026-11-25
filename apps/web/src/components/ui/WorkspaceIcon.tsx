const paths = {
  home: "m3 10 9-7 9 7v10h-6v-7H9v7H3z",
  templates: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5",
  import: "M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6",
  wizard: "M4 6h5m4 0h7M4 12h10m4 0h2M4 18h3m4 0h9M9 4v4m5 2v4m-7 2v4",
  review: "M8 3h8v5H8zM2 16h7v5H2zM15 16h7v5h-7zM12 8v4H5.5v4M12 12h6.5v4",
  analysis: "M3 20h18M6 16v-5m6 5V4m6 12V8",
  diff: "M7 4v15m-4-4 4 4 4-4m6 5V5m-4 4 4-4 4 4",
  export: "M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5",
  history: "M3 11a9 9 0 1 1 2 7M3 4v7h7m2-4v5l3 2",
  folder: "M3 6h7l2 3h9v11H3z",
  user: "M8 7a4 4 0 1 0 8 0a4 4 0 1 0-8 0M4 21v-2a8 8 0 0 1 16 0v2z",
  process: "m7 7-5 5 5 5m10-10 5 5-5 5m-4-14-2 18",
  box: "m12 3 9 5v9l-9 5-9-5V8l9-5Zm-9 5 9 5 9-5m-9 5v9",
  flow: "M3 5h4v4H3zM17 15h4v4h-4zM7 7h5v10h5",
  boundary: "M9 4H4v5m0 6v5h5m6 0h5v-5m0-6V4h-5",
  asset: "M4 5c0-4 16-4 16 0s-16 4-16 0Zm0 0v13c0 4 16 4 16 0V5m-16 7c0 4 16 4 16 0",
  plus: "M12 4v16M4 12h16",
  arrow: "M4 12h15m-6-6 6 6-6 6",
  menu: "M3 6h18M3 12h18M3 18h18",
  target: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-5 0a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
  flag: "M5 21V4m0 1c4-3 8 3 14 0v10c-5 3-10-3-14 0",
  list: "M8 6h13M8 12h13M8 18h13M3 6h1m-1 6h1m-1 6h1",
} as const;

export type WorkspaceIconName = keyof typeof paths;

export function WorkspaceIcon({ name }: Readonly<{ name: WorkspaceIconName }>) {
  return (
    <svg
      aria-hidden="true"
      className="workspace-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  );
}
