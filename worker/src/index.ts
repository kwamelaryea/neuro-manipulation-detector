/**
 * ZDrive Neuro Lens — CF Worker
 *
 * POST /analyze  — score page text via Chutes LLM, deduct 1 ZDrive credit
 * GET  /health   — liveness check
 *
 * Auth: X-ZDrive-API-Key header (beta key list) OR wallet-sig flow (future).
 * Inference: Chutes llm.chutes.ai/v1 — Qwen3-32B-TEE, same as ZDriveX.
 * Credits: on-chain consumeCredit() on Base via OPERATOR_PRIVATE_KEY.
 */

export interface Env {
  INFERENCE_BASE_URL: string;       // https://llm.chutes.ai/v1
  INFERENCE_MODEL: string;          // Qwen/Qwen3-32B-TEE
  INFERENCE_API_KEY: string;        // Chutes API key (secret)
  DEEP_SCAN_URL: string;            // https://zdrive-neuro-lens.fly.dev
  CREDITS_CONTRACT: string;         // ZDriveXCredits on Base
  BASE_RPC_URL: string;             // https://mainnet.base.org
  OPERATOR_PRIVATE_KEY: string;     // signs consumeCredit txns (secret)
  ZDRIVE_API_KEYS: string;          // comma-separated beta keys (secret)
  ENVIRONMENT?: string;
}

// ── TRIBE v2 scoring system prompt (mirrors scorer_llm.py exactly) ─────────

const SYSTEM_PROMPT = `You are a neuro-persuasion analyst. You estimate the neural and emotional response a piece of text is engineered to trigger in a reader, using the conceptual framework of Meta FAIR's TRIBE v2 brain-encoding model (arXiv:2605.04326).

# What TRIBE v2 measures (your conceptual basis)
TRIBE v2 predicts cortical vertex activations (a T x 20,484 matrix at 1Hz on the fsaverage5 surface) from video, audio, or text stimuli. We do not run it here; we reason about the constructs it captures. The two constructs that matter for manipulation detection are:

1. LIMBIC / EMOTIONAL AROUSAL — activity in limbic and salience regions:
   - amygdala: threat detection, fear, emotional salience
   - insula: visceral disgust, urgency, bodily arousal, craving
   - hippocampus: emotionally-charged memory encoding, tribal/identity recall
   High limbic activation = content engineered to provoke a fast, affective, pre-rational reaction.

2. PREFRONTAL / COGNITIVE CONTROL — activity in executive regions:
   - dlPFC (dorsolateral prefrontal cortex): deliberate reasoning, working memory, weighing evidence
   - ACC (anterior cingulate cortex): conflict monitoring, error detection, effortful evaluation
   High PFC engagement = content that invites reflection and reasoning. Manipulative content tends to SUPPRESS PFC engagement (bypass deliberation) while spiking limbic arousal.

# The manipulation index
Manipulation works by maximizing limbic arousal while minimizing prefrontal engagement — pushing the reader to act before they reason. The index is a ratio:

    manipulation_index ≈ 10 * limbic_activation / (pfc_engagement + epsilon)

where epsilon is a small constant (~0.1) that prevents division by zero. High limbic + low PFC => high manipulation. Balanced or PFC-dominant content => low manipulation. Clamp the result to the range 0–10.

# Dominant technique taxonomy
Classify the single strongest persuasion technique. Choose exactly one:
- "fear": threat, loss, danger, catastrophe framing (amygdala-driven)
- "urgency": scarcity, countdowns, "act now", FOMO (insula-driven, suppresses deliberation)
- "tribal_identity": us-vs-them, in-group signaling, identity belonging (hippocampus + amygdala)
- "reward_loop": variable reward, dopamine bait, "you won", streaks, hooks (craving circuitry)
- "neutral": informative, balanced, reflection-inviting content with no manipulative engineering

# Confidence
- "high": clear, unambiguous signals; ample text
- "medium": mixed or moderate signals
- "low": very short text, ambiguous intent, or insufficient context

# Output
Return ONLY a JSON object with exactly these fields, no prose, no markdown:
{
  "limbic_score": <float 0.0-1.0>,
  "pfc_score": <float 0.0-1.0>,
  "manipulation_index": <float 0.0-10.0>,
  "dominant_technique": <"fear"|"urgency"|"tribal_identity"|"reward_loop"|"neutral">,
  "confidence": <"low"|"medium"|"high">
}

Scoring discipline:
- limbic_score and pfc_score are independent 0–1 estimates of how strongly each system is engaged.
- manipulation_index MUST be consistent with the ratio above (limbic high + pfc low => high).
- Genuinely neutral/informative text should score limbic low, pfc moderate-to-high, manipulation_index low, technique "neutral".`;

// ── CORS ───────────────────────────────────────────────────────────────────

function corsHeaders(): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-ZDrive-API-Key',
    'Access-Control-Max-Age': '86400',
  };
}

function withCors(res: Response): Response {
  const h = new Headers(res.headers);
  for (const [k, v] of Object.entries(corsHeaders())) h.set(k, v);
  return new Response(res.body, { status: res.status, headers: h });
}

// ── Auth ───────────────────────────────────────────────────────────────────

function checkApiKey(req: Request, env: Env): boolean {
  const key = req.headers.get('X-ZDrive-API-Key');
  if (!key) return false;
  // Beta: accept any znl_ prefixed key (billing is a no-op; tighten when accounts ship)
  if (key.startsWith('znl_') && key.length >= 16) return true;
  const valid = (env.ZDRIVE_API_KEYS ?? '').split(',').map(k => k.trim()).filter(Boolean);
  if (valid.length === 0 && env.ENVIRONMENT !== 'production') return true;
  return valid.includes(key);
}

// ── On-chain credit deduction (non-blocking) ───────────────────────────────
// Mirrors ZDriveX worker's consumeCredit() — minimal viem-free implementation
// using raw eth_sendRawTransaction so we have no npm deps.

async function consumeCredit(env: Env, ctx: ExecutionContext): Promise<void> {
  if (!env.OPERATOR_PRIVATE_KEY || !env.CREDITS_CONTRACT || env.ENVIRONMENT !== 'production') return;

  ctx.waitUntil((async () => {
    try {
      // consumeCredit(address user) selector = keccak256("consumeCredit(address)")[:4]
      // For the NMD worker we record usage but don't need a user address per-call —
      // the API key maps to a user's account server-side. Use the operator address as
      // the target for now; replace with per-key wallet lookup when accounts are live.
      const selector = '0x' + await keccak256Hex('consumeCredit(address)').then(h => h.slice(0, 8));
      console.log('[billing] consumeCredit selector:', selector);
      // Full on-chain deduction requires eth_signTransaction which needs the viem/ethers
      // library. Logging only for now — wire full deduction when accounts module is ready.
    } catch (e) {
      console.error('[billing] consumeCredit error:', e);
    }
  })());
}

async function keccak256Hex(input: string): Promise<string> {
  const enc = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest('SHA-256', enc); // SHA-256 used as placeholder
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ── Inference ──────────────────────────────────────────────────────────────

function extractJson(raw: string): Record<string, unknown> {
  // Strip Qwen3 <think>…</think> blocks — greedy regex grabs braces inside them
  const stripped = raw.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  const fenced = stripped.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (fenced) return JSON.parse(fenced[1]);
  const bare = stripped.match(/\{[\s\S]*\}/);
  if (bare) return JSON.parse(bare[0]);
  throw new Error('No JSON object in model response');
}

async function callInference(text: string, env: Env): Promise<string> {
  const res = await fetch(`${env.INFERENCE_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${env.INFERENCE_API_KEY}`,
    },
    body: JSON.stringify({
      model: env.INFERENCE_MODEL,
      max_tokens: 512,
      stream: false,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT + '\n/no_think' },
        { role: 'user', content: text },
      ],
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Chutes ${res.status}: ${body.slice(0, 200)}`);
  }

  const data = await res.json() as { choices: Array<{ message: { content: string } }> };
  return data.choices?.[0]?.message?.content ?? '';
}

async function scoreText(text: string, env: Env): Promise<Record<string, unknown>> {
  const required = ['limbic_score', 'pfc_score', 'manipulation_index', 'dominant_technique', 'confidence'];

  for (let attempt = 0; attempt < 2; attempt++) {
    const content = await callInference(text, env);
    try {
      const parsed = extractJson(content);
      for (const f of required) {
        if (!(f in parsed)) throw new Error(`Missing field: ${f}`);
      }
      return { ...parsed, scorer: 'llm' };
    } catch (e) {
      if (attempt === 1) throw e;
      console.warn(`[analyze] attempt ${attempt + 1} failed, retrying:`, e);
    }
  }
  throw new Error('unreachable');
}

// ── Request handlers ───────────────────────────────────────────────────────

async function handleAnalyze(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  if (!checkApiKey(req, env)) {
    return Response.json(
      { error: 'Invalid or missing X-ZDrive-API-Key. Get your key at zdrive.io.' },
      { status: 401 }
    );
  }

  let body: { text?: string; url?: string; mode?: string };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { text, mode } = body;
  if (!text || typeof text !== 'string' || text.trim().length === 0) {
    return Response.json({ error: 'text field required' }, { status: 400 });
  }
  if (text.length > 8000) {
    return Response.json({ error: 'text too long (max 8000 chars)' }, { status: 413 });
  }

  if (mode === 'deep') {
    if (!env.DEEP_SCAN_URL) {
      return Response.json(
        { error: 'Deep scan not configured. Contact support.' },
        { status: 422 }
      );
    }
    try {
      const deepHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
      const fwdKey = req.headers.get('X-ZDrive-API-Key');
      if (fwdKey) deepHeaders['X-ZDrive-API-Key'] = fwdKey;
      const deepRes = await fetch(`${env.DEEP_SCAN_URL}/analyze`, {
        method: 'POST',
        headers: deepHeaders,
        body: JSON.stringify({ text: text.slice(0, 4000), url: body.url, mode: 'deep' }),
      });
      if (!deepRes.ok) {
        const errBody = await deepRes.text();
        throw new Error(`Deep scan ${deepRes.status}: ${errBody.slice(0, 200)}`);
      }
      const result = await deepRes.json();
      ctx.waitUntil(consumeCredit(env, ctx));
      return Response.json(result);
    } catch (e) {
      console.error('[deep-scan] error:', e);
      return Response.json({ error: String(e) }, { status: 502 });
    }
  }

  try {
    const result = await scoreText(text.slice(0, 4000), env);
    ctx.waitUntil(consumeCredit(env, ctx));
    return Response.json(result);
  } catch (e) {
    console.error('[analyze] error:', e);
    return Response.json({ error: String(e) }, { status: 502 });
  }
}

// ── Main ───────────────────────────────────────────────────────────────────

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    if (req.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(req.url);

    if (url.pathname === '/health') {
      return withCors(Response.json({
        status: 'ok',
        model: env.INFERENCE_MODEL,
        environment: env.ENVIRONMENT ?? 'unknown',
        timestamp: new Date().toISOString(),
      }));
    }

    if (url.pathname === '/analyze' && req.method === 'POST') {
      return withCors(await handleAnalyze(req, env, ctx));
    }

    return withCors(new Response('Not found', { status: 404 }));
  },
};
