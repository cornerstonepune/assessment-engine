// athena-mods: the band and the token ledger.
// One module so the band and the ledger share one reading of the session's usage.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Meter } from '../types'

const meter = atom({ plugin: 'athena-mods', key: 'meter' } as const, null)
const warned = atom({ plugin: 'athena-mods', key: 'warned' } as const, false)

export function pct(n: number | null | undefined): string {
  return n === null || n === undefined ? '-' : `${Math.round(n)}%`
}

async function readJson($: EngineInterface, path: string) {
  try {
    return JSON.parse(String(await $.fs.read(path))) as Record<string, unknown>
  } catch {
    return {} as Record<string, unknown>
  }
}

type Ctx = {
  client: string
  version: string
  grade: string
  compactions: number
  home: string
  warnAt: number
  stopAt: number
}

async function ledgerRow($: EngineInterface, ctx: Ctx, kind: string, m: Meter) {
  if (!ctx.home) return
  const now = new Date(await $.clock.now())
  const day = now.toISOString().slice(0, 10)
  const dir = `${ctx.home}/.athena/usage`
  const row = {
    ts: now.toISOString(), kind, session: await $.session.id(), repo: await $.session.cwd(),
    client: m.client, cost_usd: m.costUsd, context_percent: m.contextPercent,
    compactions: m.compactions, five_hour: m.fiveHour, seven_day: m.sevenDay,
    seven_day_reason: m.sevenDay === null
      ? 'the plan reported no weekly figure' : null,
  }
  const file = `${dir}/${day}.jsonl`
  let prior = ''
  try { prior = String(await $.fs.read(file)) } catch { prior = '' }
  await $.fs.write(file, prior + JSON.stringify(row) + '\n')
  await $.fs.write(`${dir}/latest.json`, JSON.stringify({
    ...row, week_warn_percent: ctx.warnAt, week_stop_percent: ctx.stopAt,
    automation: m.sevenDay !== null && m.sevenDay >= ctx.stopAt ? 'urgent-only' : 'normal',
  }, null, 2) + '\n')
}

async function refresh($: EngineInterface, ctx: Ctx): Promise<Meter> {
  const usage = await $.session.usage()
  const sevenDay = usage.rateLimits.find(r => r.kind === 'seven_day')
  const fiveHour = usage.rateLimits.find(r => r.kind === 'five_hour')
  const m: Meter = {
    client: ctx.client, version: ctx.version, grade: ctx.grade, compactions: ctx.compactions,
    contextPercent: usage.context.percent ?? null,
    costUsd: usage.cost ? Math.round(usage.cost.usd * 100) / 100 : null,
    fiveHour: fiveHour?.percentUsed ?? null,
    sevenDay: sevenDay?.percentUsed ?? null,
    sevenDayResets: sevenDay?.resetsAt ?? null,
  }
  await update($, meter, () => m)
  if (m.sevenDay !== null && m.sevenDay >= ctx.warnAt && !(await read($, warned))) {
    await update($, warned, () => true)
    $.ui.toast(`Plan usage this week is at ${pct(m.sevenDay)} (warning line ${ctx.warnAt}%).`)
  }
  return m
}

export const register: Register = (on, options) => {
  const ctx: Ctx = {
    client: '', version: '', grade: '', compactions: 0, home: '',
    warnAt: Number(options.week_warn_percent ?? 75),
    stopAt: Number(options.week_stop_percent ?? 90),
  }

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    ctx.home = (await $.env.get('HOME')) ?? ''
    const config = await readJson($, '.claude/athena/config.json')
    const manifest = await readJson($, '.claude/athena/MANIFEST.json')
    const assurance = await readJson($, '.athena/assurance.json')
    ctx.client = typeof config.client === 'string' ? config.client : ''
    ctx.version = typeof manifest.athena === 'string' ? manifest.athena : ''
    ctx.grade = typeof assurance.grade === 'string' ? assurance.grade : ''
    ctx.compactions = 0
    return result
  })

  on('session.compact', async ($, e, next) => {
    const result = await next(e)
    ctx.compactions += 1
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    try {
      await ledgerRow($, ctx, 'turn', await refresh($, ctx))
    } catch {
      // The ledger is best-effort: a full disk must never break a turn.
    }
    return result
  })

  on('session.end', async ($, e, next) => {
    try {
      await ledgerRow($, ctx, 'session', await refresh($, ctx))
    } catch {
      // best-effort
    }
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const m = await read($, meter)
    if (e.props.hasSurvey || (!m && !ctx.client)) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    const week = m?.sevenDay ?? null
    const hot = week !== null && week >= ctx.warnAt
    const resets = m?.sevenDayResets ? ` (resets ${m.sevenDayResets.slice(5, 16).replace('T', ' ')})` : ''
    const parts = [
      `athena ${ctx.version || '?'}`,
      ctx.client ? `client ${ctx.client}` : null,
      ctx.grade ? `assurance ${ctx.grade}` : null,
      `context ${pct(m?.contextPercent)}`,
      `compactions ${ctx.compactions}`,
      m?.costUsd !== null && m?.costUsd !== undefined ? `session $${m.costUsd.toFixed(2)}` : null,
      `5h ${pct(m?.fiveHour)}`,
    ].filter(Boolean).join(' · ')
    return (
      <Box>
        <Text dimColor>{parts} · </Text>
        <Text color={hot ? 'red' : undefined} dimColor={!hot}>week {pct(week)}{resets}</Text>
      </Box>
    )
  })
}
