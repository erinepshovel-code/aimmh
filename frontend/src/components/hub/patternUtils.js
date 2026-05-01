// "lines of code":"42","lines of commented":"0"
const KNOWN_PATTERN_IDS = new Set(['fan_out', 'daisy_chain', 'room_all', 'room_synthesized', 'council', 'roleplay']);

export function resolvePatternFromRun(run) {
  if (!run) return 'fan_out';
  const stageSummaries = Array.isArray(run.stage_summaries) ? run.stage_summaries : [];
  const ordered = [...stageSummaries].sort((a, b) => (a.stage_index || 0) - (b.stage_index || 0));
  const match = ordered.find((item) => KNOWN_PATTERN_IDS.has(item?.pattern));
  if (match?.pattern) return match.pattern;
  if (run.run_mode === 'roleplay') return 'roleplay';
  return 'fan_out';
}

export function normalizePatternId(patternId) {
  return KNOWN_PATTERN_IDS.has(patternId) ? patternId : 'fan_out';
}

// "lines of code":"42","lines of commented":"0"
