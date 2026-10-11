<script lang="ts">
	import { get, post, put, conn, bump } from '#lib/api.svelte.ts';
	import { LABEL, O } from '#lib/format.ts';
	import PageHead from '#lib/components/PageHead.svelte';
	import type { Effect, Keyword, KeywordsResponse } from '#lib/types.ts';

	let data = $state<KeywordsResponse | null>(null);
	let sel = $state('');
	let draft = $state<Keyword[]>([]);
	let dirty = $state(false);
	let result = $state<{
		effect: Effect;
		hits: { before: number; after: number; per_keyword?: Record<string, number> };
		saved?: boolean;
	} | null>(null);
	let error = $state('');
	let busy = $state(false);

	$effect(() => {
		conn.epoch;
		get<KeywordsResponse>('/api/keywords').then((d) => {
			data = d;
			if (!sel && d.families.length) sel = d.families[0].id;
			if (!dirty) reset(true);
		}).catch((e) => (error = e.message));
	});

	let fam = $derived(data?.families.find((f) => f.id === sel) ?? null);

	function reset(keepResult = false) {
		const f = data?.families.find((x) => x.id === sel);
		draft = f ? structuredClone($state.snapshot(f.keywords)) as Keyword[] : [];
		dirty = false;
		if (!keepResult) {
			result = null;
			error = '';
		}
	}

	function pick(id: string) {
		if (dirty && !confirm('Discard unsaved keyword changes?')) return;
		sel = id;
		dirty = false;
		reset();
	}

	const list = (a: string[] | undefined) => (a ?? []).join(', ');
	const parse = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean);

	function edit(i: number, k: 'de' | 'gsw' | 'en', v: string) {
		draft[i][k] = parse(v);
		dirty = true;
	}

	function add() {
		draft.push({ label: '', enabled: true, case_sensitive: false, de: [], gsw: [], en: [], harmless: [] });
		dirty = true;
	}

	async function run(save: boolean) {
		busy = true;
		error = '';
		const body = { family: sel, keywords: $state.snapshot(draft), author: conn.user || 'officer' };
		try {
			result = save ? await put('/api/keywords', body) : await post('/api/keywords/preview', body);
			if (save) {
				dirty = false;
				bump();
			}
		} catch (e: any) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Keywords · Sherlock Phones</title></svelte:head>

<PageHead n="04 Settings" title="Keywords" lead="Words that mark a passage for listening." />

<div class="grid kw">
	<nav class="fams" aria-label="Categories">
		<ol>
			{#each data?.families ?? [] as f}
				{@const nh = f.keywords.reduce((s, k) => s + (k.hits ?? 0), 0)}
				<li>
					<button class:on={f.id === sel} onclick={() => pick(f.id)} aria-current={f.id === sel}>
						<span class="fl">{f.label}</span>
						<span class="small muted num">{f.keywords.length} {f.keywords.length === 1 ? 'keyword' : 'keywords'} · {nh} {nh === 1 ? 'hit' : 'hits'}</span>
					</button>
				</li>
			{/each}
		</ol>
	</nav>

	<section class="ed" aria-label="Keywords of {fam?.label ?? ''}">
		<table>
			<thead>
				<tr>
					<th scope="col">On</th>
					<th scope="col">Name</th>
					<th scope="col">Standard German</th>
					<th scope="col">Swiss German</th>
					<th scope="col">English</th>
					<th scope="col" class="r">Hits</th>
				</tr>
			</thead>
			<tbody>
				{#each draft as k, i}
					<tr class:off={!k.enabled}>
						<td><input type="checkbox" bind:checked={k.enabled} onchange={() => (dirty = true)} aria-label="Keyword {k.label} enabled" /></td>
						<td><input class="field" bind:value={k.label} oninput={() => (dirty = true)} aria-label="Name" placeholder="Name" /></td>
						<td><textarea class="field ta" rows="1" value={list(k.de)} onchange={(e) => edit(i, 'de', e.currentTarget.value)} aria-label="Standard German words"></textarea></td>
						<td><textarea class="field ta" rows="1" value={list(k.gsw)} onchange={(e) => edit(i, 'gsw', e.currentTarget.value)} aria-label="Swiss German words"></textarea></td>
						<td><textarea class="field ta" rows="1" value={list(k.en)} onchange={(e) => edit(i, 'en', e.currentTarget.value)} aria-label="English words"></textarea></td>
						<td class="r num h">
							{k.id ? (k.hits ?? 0) : 'new'}
							{#if !result?.saved && result?.hits.per_keyword && k.id && (result.hits.per_keyword[k.id] ?? 0) !== (k.hits ?? 0)}
								<span class="red">→ {result.hits.per_keyword[k.id] ?? 0}</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="small muted hint">Separate words with commas.</p>

		<div class="bar">
			<button class="btn" onclick={add}>+ Keyword</button>
			<span class="sp"></span>
			{#if dirty}<button class="btn link small" onclick={() => reset()}>Discard</button>{/if}
			<button class="btn" onclick={() => run(false)} disabled={busy}>See effect</button>
			<button class="btn primary" onclick={() => run(true)} disabled={busy || !dirty}>Save</button>
		</div>

		<div class="res" aria-live="polite">
			{#if error}
				<p class="red">{error}</p>
			{:else if result}
				<p class="label">{result.saved ? 'Saved · applied to all stored calls now' : 'Effect if saved'}</p>
				<p class="h2">{result.effect.summary}</p>
				<p class="small muted num">Keyword hits in this category {result.hits.before} → {result.hits.after}</p>
				{#if result.effect.changed.length}
					<ul class="small num">
						{#each result.effect.changed as c}
							<li><a href="/calls/{encodeURIComponent(c.id)}">{c.id}</a> <span class={O[c.before]}>{LABEL[c.before]}</span> → <span class={O[c.after]}>{LABEL[c.after]}</span></li>
						{/each}
					</ul>
				{/if}
			{/if}
		</div>
	</section>
</div>

<style>
	.kw {
		margin-top: 48px;
		align-items: start;
	}
	.fams {
		grid-column: 1 / span 3;
		position: sticky;
		top: 120px;
	}
	.fams ol {
		border-top: var(--rule);
	}
	.fams button {
		display: block;
		width: 100%;
		text-align: left;
		background: none;
		border: 0;
		border-bottom: var(--hair);
		padding: 12px 0 12px 12px;
		cursor: pointer;
	}
	.fams button:hover {
		background: var(--grey-1);
	}
	.fams button.on {
		box-shadow: inset 4px 0 0 var(--red);
	}
	.fl {
		display: block;
		font-weight: 600;
		font-size: var(--t-l);
		letter-spacing: -0.01em;
	}
	.ed {
		grid-column: 4 / span 9;
	}
	table {
		width: 100%;
		border-collapse: collapse;
	}
	th {
		text-align: left;
		font-size: var(--t-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		padding: 8px 12px 8px 0;
		border-bottom: var(--rule);
	}
	td {
		padding: 6px 12px 6px 0;
		border-bottom: var(--hair);
	}
	td .field {
		border: 1px solid var(--grey-2);
		padding: 4px 6px;
		font-size: var(--t-s);
		background: var(--white);
	}
	td .field:hover {
		border-color: var(--grey-3);
	}
	td .field:focus {
		border-color: var(--red);
	}
	.ta {
		field-sizing: content;
		min-height: 0;
		resize: none;
		line-height: 1.4;
	}
	td {
		vertical-align: top;
	}
	tr.off .field {
		color: var(--grey-ink);
		text-decoration: line-through;
	}
	input[type='checkbox'] {
		width: 16px;
		height: 16px;
		accent-color: var(--black);
	}
	.r {
		text-align: right;
	}
	.h {
		white-space: nowrap;
		font-weight: 600;
	}
	.hint {
		margin-top: 8px;
	}
	.bar {
		display: flex;
		gap: 12px;
		align-items: center;
		margin-top: 24px;
	}
	.sp {
		flex: 1;
	}
	.res {
		margin-top: 32px;
		border-top: var(--rule);
		padding-top: 12px;
		min-height: 80px;
	}
	.res .h2 {
		margin: 4px 0 8px;
	}
	.res li {
		padding: 3px 0;
		border-bottom: var(--hair);
	}
	@media (max-width: 1100px) {
		.fams,
		.ed {
			grid-column: 1 / span 12;
			position: static;
		}
		.ed {
			margin-top: 24px;
		}
	}
</style>
