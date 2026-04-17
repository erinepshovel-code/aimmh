// "lines of code":"18","lines of commented":"0"
export const estimateTokens = (text = '') => {
  const clean = String(text || '').trim();
  if (!clean) return 1;
  return Math.max(1, Math.round(clean.length / 4));
};

export const inferDeveloper = (modelId = '') => {
  const id = String(modelId || '').toLowerCase();
  if (id.startsWith('gpt') || id.startsWith('o1') || id.startsWith('o3')) return 'openai';
  if (id.startsWith('claude')) return 'anthropic';
  if (id.startsWith('gemini')) return 'google';
  return 'unknown';
};

export const responseTokenTotal = (response, promptText) => {
  if (typeof response?.total_tokens === 'number') return response.total_tokens;
  const promptTokens = typeof response?.prompt_tokens === 'number' ? response.prompt_tokens : estimateTokens(promptText);
  const completionTokens = typeof response?.completion_tokens === 'number' ? response.completion_tokens : estimateTokens(response?.content || '');
  return promptTokens + completionTokens;
};
// "lines of code":"18","lines of commented":"0"
