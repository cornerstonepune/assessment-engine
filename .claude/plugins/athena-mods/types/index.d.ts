export type Meter = {
  client: string
  version: string
  grade: string
  contextPercent: number | null
  compactions: number
  costUsd: number | null
  fiveHour: number | null
  sevenDay: number | null
  sevenDayResets: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'athena-mods': { meter: Meter | null; warned: boolean }
  }
}
