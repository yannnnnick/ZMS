import type { ReactNode } from "react";

export type IconName =
  | "grid"
  | "paw"
  | "leaf"
  | "shield"
  | "clock"
  | "heart"
  | "check"
  | "file"
  | "logout"
  | "login"
  | "plus"
  | "alert"
  | "trash";

const paths: Record<IconName, ReactNode> = {
  grid: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  paw: (
    <path d="M8 9c1.2 0 2-1.1 2-2.5S9.2 4 8 4 6 5.1 6 6.5 6.8 9 8 9Zm8 0c1.2 0 2-1.1 2-2.5S17.2 4 16 4s-2 1.1-2 2.5.8 2.5 2 2.5ZM5 14c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2Zm14 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2Zm-7 1c-2.9 0-5 1.7-5 4 0 1.6 1.1 2 2.5 2 .9 0 1.5-.4 2.5-.4s1.6.4 2.5.4c1.4 0 2.5-.4 2.5-2 0-2.3-2.1-4-5-4Z" />
  ),
  leaf: <path d="M20 4c-7.2.2-12 3.9-12 9.7 0 2.1 1.1 3.9 2.8 5C12.4 14.4 15 10.8 19 8c-3 3.4-5.2 7-6.4 11.3C17.2 18.5 21 13.4 20 4ZM4 20c1.7-.6 3.1-1.3 4.4-2.3" />,
  shield: <path d="M12 3 20 6v6c0 5-3.4 8.2-8 9-4.6-.8-8-4-8-9V6l8-3Zm0 4v10" />,
  clock: <path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l3 2" />,
  heart: <path d="M12 21s-8-4.7-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 6.3-8 11-8 11Z" />,
  check: <path d="m5 12 4 4L19 6" />,
  file: <path d="M6 3h8l4 4v14H6zM14 3v5h4M8 13h8M8 17h6" />,
  logout: <path d="M10 17v2H5V5h5v2M14 8l4 4-4 4M18 12H9" />,
  login: <path d="M14 7V5h5v14h-5v-2M10 8l4 4-4 4M14 12H5" />,
  plus: <path d="M12 5v14M5 12h14" />,
  alert: <path d="M12 3 22 20H2L12 3Zm0 6v5m0 3h.01" />,
  trash: <path d="M4 7h16M9 7V5h6v2m-8 3 1 10h8l1-10" />
};

export function Icon({ name }: { name: IconName }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {paths[name]}
    </svg>
  );
}
