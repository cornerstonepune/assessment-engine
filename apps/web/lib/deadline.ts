// How long a page waits for the database before it says so in words (app/error.tsx) instead of
// hanging until Vercel's five-minute limit. The query may still be running on the server; the
// person is no longer waiting on it.
export const PAGE_WAIT_MS = 8_000;

export class DatabaseSlow extends Error {
  constructor(ms: number) {
    super(`The database did not answer within ${ms / 1000} seconds.`);
    this.name = "DatabaseSlow";
  }
}

export function deadline<T>(work: Promise<T>, ms = PAGE_WAIT_MS): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const late = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new DatabaseSlow(ms)), ms);
  });
  return Promise.race([work, late]).finally(() => clearTimeout(timer));
}
