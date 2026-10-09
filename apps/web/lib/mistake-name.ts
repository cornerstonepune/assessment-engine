// A named mistake by the database's one rule, `mistake_name` (migration 20261027090000), which the engine's own
// lookup is held to by a test: the name for the question's own operation, else for the operation of the skill the
// mistake was charged to; failing that, its name for any operation, else the one name it has, else its code.
// `names` is `misconceptionNames()`, every answer of that rule computed by the database — keyed `code@op` for each
// operation, `code|skill` for each operation's skill, and `code` for neither — so nothing here re-decides it. `op` is
// the question's operation as `operation_sign` folds it. Another operation's name would be a wrong statement about
// the child.
export function mistakeName(names: Record<string, string>, code: string, op?: string | null, skill?: string | null): string {
  if (op && names[`${code}@${op}`]) return names[`${code}@${op}`];
  return names[`${code}|${skill}`] ?? names[code] ?? code;
}
