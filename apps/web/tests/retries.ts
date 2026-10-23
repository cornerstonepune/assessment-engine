/**
 * How many times a failed browser test is run again: once in CI, never on a laptop. A test that fails and then passes is
 * reported flaky (bin/ci-flaky-summary lists it); one that fails twice fails the job (docs/adr/0094).
 */
export const retriesFor = (ci: string | undefined): number => (ci ? 1 : 0);
