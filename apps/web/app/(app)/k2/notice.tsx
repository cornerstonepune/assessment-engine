// One quiet notice for the K2 pages: a refusal or an empty state, said once. Monsoon, not the site's green EmptyState: green
// reads as "done", and nothing here is done or wrong (a child not seen is only not seen).
export function Notice({ children, flush }: { children: React.ReactNode; flush?: boolean }) {
  return (
    <p role="status" data-ux="empty" className={`${flush ? "" : "mb-4 "}border border-monsoon/30 bg-monsoon/10 p-3 text-[13.5px]`}>
      {children}
    </p>
  );
}
