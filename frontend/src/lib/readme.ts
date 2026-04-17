// "lines of code":"37","lines of commented":"9"
/**
 * Dynamic README assembler.
 *
 * What:
 * - Converts backend registry payload into coherent markdown.
 *
 * How:
 * - Builds overview, violations, module summaries, and function docs.
 */

export function buildReadmeMarkdown(registry, userQuestion) {
  const modules = Array.isArray(registry?.modules) ? registry.modules : [];
  const violations = Array.isArray(registry?.violations) ? registry.violations : [];

  const header = [
    '# AIMMH Dynamic README',
    '',
    `Generated modules: ${registry?.module_count || modules.length}`,
    `Violations: ${violations.length}`,
    '',
    userQuestion ? `User ask: ${userQuestion}` : 'User ask: (none)',
    '',
  ];

  const violationBlock = violations.length === 0
    ? ['## Compliance', '', '- ✅ All scanned modules satisfy current rule checks.', '']
    : [
      '## Compliance',
      '',
      ...violations.slice(0, 60).map((v) => `- ❌ ${v.path} (code=${v.lines_of_code}, top=${v.marker_top_ok}, bottom=${v.marker_bottom_ok})`),
      '',
    ];

  const moduleBlocks = modules.slice(0, 120).flatMap((m) => {
    const fnDocs = Array.isArray(m.functions) ? m.functions.slice(0, 12) : [];
    return [
      `## Module: ${m.path}`,
      '',
      `- Code lines: ${m.lines_of_code}`,
      `- Commented lines: ${m.lines_of_commented}`,
      `- Rule <=400 code: ${m.max_code_rule_ok ? 'yes' : 'no'}`,
      `- Marker top/bottom: ${m.marker_top_ok ? 'ok' : 'missing'} / ${m.marker_bottom_ok ? 'ok' : 'missing'}`,
      m.module_doc ? `- What/How: ${String(m.module_doc).replace(/\n+/g, ' ').slice(0, 600)}` : '- What/How: (no module doc found)',
      '',
      ...fnDocs.map((f) => `  - ${f.name}: ${f.doc ? String(f.doc).replace(/\n+/g, ' ').slice(0, 300) : '(no doc)'}`),
      '',
    ];
  });

  return [...header, ...violationBlock, ...moduleBlocks].join('\n');
}

// "lines of code":"37","lines of commented":"9"
