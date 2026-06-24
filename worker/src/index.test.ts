import { describe, it, expect } from 'vitest';
import { extractJson, checkApiKey } from './index';
import type { Env } from './index';

// ── extractJson ──────────────────────────────────────────────────────────────

describe('extractJson', () => {
  it('parses clean JSON', () => {
    const r = extractJson('{"limbic_score":0.5,"pfc_score":0.3}');
    expect(r.limbic_score).toBe(0.5);
    expect(r.pfc_score).toBe(0.3);
  });

  it('parses fenced JSON', () => {
    const r = extractJson('```json\n{"limbic_score":0.8}\n```');
    expect(r.limbic_score).toBe(0.8);
  });

  it('parses fenced JSON without language tag', () => {
    const r = extractJson('```\n{"limbic_score":0.8}\n```');
    expect(r.limbic_score).toBe(0.8);
  });

  it('strips Qwen3 thinking tags before extracting', () => {
    const input = '<think>\nLet me analyze {"fake": true} this text...\n</think>\n{"limbic_score":0.7,"pfc_score":0.4}';
    const r = extractJson(input);
    expect(r.limbic_score).toBe(0.7);
    expect(r.pfc_score).toBe(0.4);
  });

  it('strips multiple thinking blocks', () => {
    const input = '<think>first block {"x":1}</think>\n<think>second {"y":2}</think>\n{"limbic_score":0.1}';
    const r = extractJson(input);
    expect(r.limbic_score).toBe(0.1);
  });

  it('handles thinking tags with curly braces inside', () => {
    const input = '<think>\nI need to produce {"limbic_score": ...}\nLet me think about the JSON format: {"key": "value"}\n</think>\n\n{"limbic_score":0.9,"pfc_score":0.2,"manipulation_index":8.5,"dominant_technique":"fear","confidence":"high"}';
    const r = extractJson(input);
    expect(r.limbic_score).toBe(0.9);
    expect(r.dominant_technique).toBe('fear');
  });

  it('throws on empty string', () => {
    expect(() => extractJson('')).toThrow('No JSON object');
  });

  it('throws on thinking-only response (no JSON after)', () => {
    expect(() => extractJson('<think>I cannot do this task</think>')).toThrow('No JSON object');
  });

  it('throws on plain text with no JSON', () => {
    expect(() => extractJson('I cannot generate this content.')).toThrow('No JSON object');
  });

  it('parses JSON with extra whitespace', () => {
    const r = extractJson('  \n  { "limbic_score" : 0.5 }  \n  ');
    expect(r.limbic_score).toBe(0.5);
  });

  it('handles JSON after prose (no thinking tags)', () => {
    const input = 'Here is the analysis:\n{"limbic_score":0.3,"pfc_score":0.7}';
    const r = extractJson(input);
    expect(r.limbic_score).toBe(0.3);
  });
});

// ── checkApiKey ──────────────────────────────────────────────────────────────

function makeReq(key?: string): Request {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  if (key) headers.set('X-ZDrive-API-Key', key);
  return new Request('https://example.com/analyze', { method: 'POST', headers });
}

function makeEnv(overrides: Partial<Env> = {}): Env {
  return {
    INFERENCE_BASE_URL: 'https://llm.chutes.ai/v1',
    INFERENCE_MODEL: 'Qwen/Qwen3-32B-TEE',
    INFERENCE_API_KEY: 'test',
    DEEP_SCAN_URL: 'https://zdrive-neuro-lens.fly.dev',
    CREDITS_CONTRACT: '',
    BASE_RPC_URL: 'https://mainnet.base.org',
    OPERATOR_PRIVATE_KEY: '',
    ZDRIVE_API_KEYS: '',
    ENVIRONMENT: 'production',
    ...overrides,
  };
}

describe('checkApiKey', () => {
  it('rejects missing key', () => {
    expect(checkApiKey(makeReq(), makeEnv())).toBe(false);
  });

  it('rejects empty string key', () => {
    expect(checkApiKey(makeReq(''), makeEnv())).toBe(false);
  });

  it('accepts valid znl_ key (>=16 chars)', () => {
    expect(checkApiKey(makeReq('znl_db3dabcdef1234'), makeEnv())).toBe(true);
  });

  it('accepts long znl_ key', () => {
    expect(checkApiKey(makeReq('znl_db332aae528e3b1bfc56aa434f2fcb17'), makeEnv())).toBe(true);
  });

  it('rejects short znl_ key (<16 chars)', () => {
    expect(checkApiKey(makeReq('znl_short'), makeEnv())).toBe(false);
  });

  it('rejects exactly 15 char znl_ key', () => {
    expect(checkApiKey(makeReq('znl_12345678901'), makeEnv())).toBe(false); // 15 chars
  });

  it('accepts exactly 16 char znl_ key', () => {
    expect(checkApiKey(makeReq('znl_123456789012'), makeEnv())).toBe(true); // 16 chars
  });

  it('rejects non-znl prefix', () => {
    expect(checkApiKey(makeReq('sk_random_key_1234567890'), makeEnv())).toBe(false);
  });

  it('accepts exact match from ZDRIVE_API_KEYS list', () => {
    const env = makeEnv({ ZDRIVE_API_KEYS: 'key1,key2,key3' });
    expect(checkApiKey(makeReq('key2'), env)).toBe(true);
  });

  it('rejects key not in ZDRIVE_API_KEYS list (non-znl)', () => {
    const env = makeEnv({ ZDRIVE_API_KEYS: 'key1,key2' });
    expect(checkApiKey(makeReq('key3'), env)).toBe(false);
  });

  it('allows any key in dev mode with no keys configured', () => {
    const env = makeEnv({ ZDRIVE_API_KEYS: '', ENVIRONMENT: 'development' });
    expect(checkApiKey(makeReq('anything_here_123'), env)).toBe(true);
  });

  it('rejects unknown key in production even with no keys configured', () => {
    const env = makeEnv({ ZDRIVE_API_KEYS: '', ENVIRONMENT: 'production' });
    expect(checkApiKey(makeReq('not_znl_prefix'), env)).toBe(false);
  });
});
