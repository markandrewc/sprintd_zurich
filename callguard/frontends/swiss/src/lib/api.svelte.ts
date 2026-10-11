// Fetch layer. Talks to the callguard API (proxied at /api by vite).
// Sample data (static copies in /fixtures) is used ONLY when the build is forced to it with VITE_USE_FIXTURES=1;
// then every page shows a "sample data" banner and writes are refused. If the API is unreachable or fails, the
// app shows an error banner instead: it never switches to sample data on its own, and never fakes a save.
// No decision logic lives here.

import type { CallRow, Rulebook, RulebookPut } from './types';

export const FORCE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === '1';

function clientId(): string {
	if (typeof sessionStorage === 'undefined') return 'swiss';
	let id = sessionStorage.getItem('sp-client');
	if (!id) {
		id = 'swiss-' + Math.random().toString(36).slice(2, 10);
		sessionStorage.setItem('sp-client', id);
	}
	return id;
}

export const conn = $state({
	mode: (FORCE_FIXTURES ? 'fixtures' : 'unknown') as 'unknown' | 'live' | 'down' | 'fixtures',
	/** why the API is down (shown in the banner) */
	error: '',
	/** what the API serves (from /api/meta): shown next to the live indicator */
	source: null as null | { profile: string; runs_dir: string; calls: number },
	/** which rule book decides (production or the in-memory demo book), from /api/meta and /api/rulebook */
	rulebook: null as null | Rulebook,
	user: (typeof localStorage !== 'undefined' && localStorage.getItem('sp-user')) || '',
	/** bumps whenever settings / rules / keywords change, so views refetch */
	epoch: 0
});

export function setUser(name: string) {
	conn.user = name;
	localStorage.setItem('sp-user', name);
}

export function bump() {
	conn.epoch++;
}

let probing: Promise<void> | null = null;

function down(msg: string) {
	conn.mode = 'down';
	conn.error = msg;
}

export function probe(): Promise<void> {
	if (FORCE_FIXTURES) {
		conn.mode = 'fixtures';
		return Promise.resolve();
	}
	probing ??= (async () => {
		try {
			const r = await fetch('/api/meta', { signal: AbortSignal.timeout(30000) });
			const ok = r.ok && (r.headers.get('content-type') ?? '').includes('json');
			if (!ok) {
				down(`/api/meta answered ${r.status} ${r.statusText}`.trim());
				return;
			}
			const m = await r.json();
			conn.source = { profile: m.profile, runs_dir: m.runs_dir, calls: m.counts?.calls ?? 0 };
			conn.rulebook = m.rulebook ?? null;
			conn.mode = 'live';
			conn.error = '';
		} catch (e: any) {
			down(e?.name === 'TimeoutError' ? 'no answer from /api/meta within 30 s' : String(e?.message ?? e));
		}
	})().finally(() => (probing = null));
	return probing;
}

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

// ---------- fixtures ----------

const cache = new Map<string, Promise<unknown>>();

function fixture<T>(name: string): Promise<T> {
	if (!cache.has(name)) {
		cache.set(
			name,
			fetch(`/fixtures/${name}.json`).then((r) => {
				if (!r.ok) throw new ApiError(404, `fixture ${name} missing`);
				return r.json();
			})
		);
	}
	return cache.get(name) as Promise<T>;
}

async function fromFixtures(method: string, path: string, body?: unknown): Promise<any> {
	const url = new URL(path, 'http://x');
	const p = url.pathname;
	const q = url.searchParams;
	const any = (n: string) => fixture<any>(n);

	if (method === 'GET') {
		if (p === '/api/meta') return any('meta');
		if (p === '/api/calls') {
			const d = structuredClone(await any('calls'));
			const status = q.get('status');
			const fam = q.get('family');
			const rev = q.get('reviewed');
			const s = (q.get('q') ?? '').toLowerCase();
			d.calls = d.calls.filter(
				(c: CallRow) =>
					(!status ||
						(status === 'flagged' ? c.label !== 'no_alert' : c.label === status)) &&
					(!fam || c.family === fam) &&
					(!rev || String(c.reviewed) === rev) &&
					(!s || (c.id + ' ' + c.reason).toLowerCase().includes(s))
			);
			return d;
		}
		if (/^\/api\/calls\/[^/]+$/.test(p)) {
			// three captured calls (alarm / review / no alert); others borrow the one with their label
			const cid = decodeURIComponent(p.split('/').pop()!);
			const list = (await any('calls')).calls as CallRow[];
			const label = list.find((c) => c.id === cid)?.label ?? 'alarm';
			return structuredClone(await any('call_detail_' + label));
		}
		const map: Record<string, string> = {
			'/api/settings': 'settings',
			'/api/summary': 'summary',
			'/api/rules': 'rules',
			'/api/facts': 'facts',
			'/api/keywords': 'keywords',
			'/api/how-it-works': 'how_it_works'
		};
		if (map[p]) return any(map[p]);
	} else {
		// previews only show the captured sample numbers; anything that would change something is refused
		if (p === '/api/rules/preview') return any('rules_preview');
		if (p === '/api/keywords/preview') return any('keywords_preview');
		throw new ApiError(409, 'Sample data (VITE_USE_FIXTURES=1): nothing can be saved or changed. Start the API to work on real results.');
	}
	throw new ApiError(404, `no fixture for ${method} ${p}`);
}

// ---------- public ----------

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
	const method = init.method ?? 'GET';
	if (conn.mode === 'fixtures') return fromFixtures(method, path, init.body);
	if (conn.mode === 'unknown') await probe();
	if ((conn.mode as string) === 'down') throw new ApiError(503, 'API nicht erreichbar: ' + conn.error);

	const headers: Record<string, string> = { 'X-Client': clientId() };
	if (conn.user) headers['X-User'] = conn.user;
	if (init.body !== undefined) headers['Content-Type'] = 'application/json';
	let r: Response;
	try {
		r = await fetch(path, {
			method,
			headers,
			body: init.body === undefined ? undefined : JSON.stringify(init.body)
		});
	} catch (e: any) {
		down(String(e?.message ?? e));
		throw new ApiError(503, 'API nicht erreichbar: ' + conn.error);
	}
	if (r.status === 502 || r.status === 503 || r.status === 504) {
		// the vite proxy answers 502 when the API process is gone
		down(`${method} ${path} answered ${r.status}`);
		throw new ApiError(r.status, 'API nicht erreichbar: ' + conn.error);
	}
	const data = await r.json().catch(() => ({}));
	if (!r.ok) throw new ApiError(r.status, (data as any)?.detail ?? r.statusText);
	return data;
}

export const get = <T>(path: string) => api<T>(path);
export const post = <T>(path: string, body: unknown) => api<T>(path, { method: 'POST', body });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: 'PUT', body });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body });
export const del = <T>(path: string) => api<T>(path, { method: 'DELETE' });

/** Re-read which rule book decides (after a rule change or a switch). */
export async function refreshRulebook(): Promise<void> {
	if (conn.mode === 'fixtures') return;
	try {
		conn.rulebook = await get<Rulebook>('/api/rulebook');
	} catch {
		/* the banner shows a down API */
	}
}

/** Switch the rule book: 'demo' = an EMPTY in-memory demo book, 'production' = the full rule book.
 * Nothing is written to the rule book file. Every view refetches. */
export async function setRulebook(mode: 'demo' | 'production'): Promise<RulebookPut> {
	const r = await put<RulebookPut>('/api/rulebook', { mode });
	conn.rulebook = r.rulebook;
	bump();
	return r;
}

export function audioSrc(url: string): string | null {
	return conn.mode === 'live' ? url : null;
}
