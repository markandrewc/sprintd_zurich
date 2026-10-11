<script lang="ts">
	import { get, put, conn, probe, bump } from '#lib/api.svelte.ts';
	import { LABEL, SQ, O, time, stripRule } from '#lib/format.ts';
	import { goto } from '$app/navigation';
	import Spread from '#lib/components/Spread.svelte';
	import type { CallsResponse, CallRow, Counts, Change, Meta, Settings, SettingsPut, Summary, Label } from '#lib/types.ts';

	let meta = $state<Meta | null>(null);
	let summary = $state<Summary | null>(null);
	let settings = $state<Settings | null>(null);
	let list = $state<CallsResponse | null>(null);
	let counts = $state<Counts | null>(null);
	let changed = $state<Change[]>([]);
	let th = $state(0.55);
	let cert = $state(0.6);
	let busy = $state(false);

	let listEpoch = $state(0);

	// call sets (PUT /api/callset): which run folder the dashboard shows; rules and sliders apply to that one
	let sets = $state<{ id: string; calls: number; active: boolean }[]>([]);
	let setBusy = $state(false);
	$effect(() => {
		conn.epoch;
		get<{ call_sets: typeof sets }>('/api/callsets').then((r) => (sets = r.call_sets)).catch(() => {});
	});
	async function useSet(id: string) {
		setBusy = true;
		try {
			await put('/api/callset', { id });
			status = '';
			changed = [];
			await probe();
			bump();
		} catch (e: any) {
			cutErr = e.message;
		} finally {
			setBusy = false;
		}
	}

	// filters
	let status = $state<'' | 'flagged' | Label>('');
	let family = $state('');
	let reviewed = $state<'' | 'true' | 'false'>('');
	let q = $state('');

	$effect(() => {
		conn.epoch;
		get<Meta>('/api/meta').then((m) => (meta = m)).catch(() => {});
		get<Settings>('/api/settings').then((s) => {
			settings = s;
			th = s.threshold;
			cert = s.certainty ?? 0.6;
		}).catch(() => {});
		loadSummary();
	});

	function loadSummary() {
		return get<Summary>('/api/summary').then((s) => {
			summary = s;
			counts = s.counts;
		}).catch(() => {});
	}

	// demo rule book: calls flagged although no rule decided them (keyword / pattern cues alone)
	let demo = $derived(conn.rulebook?.mode === 'demo');
	let flaggedNoRule = $state<CallRow[]>([]);
	$effect(() => {
		conn.epoch;
		listEpoch;
		if (!demo) return;
		get<CallsResponse>('/api/calls?status=flagged')
			.then((r) => (flaggedNoRule = r.calls.filter((x) => !x.rule_id)))
			.catch(() => {});
	});

	let qDebounced = $state('');
	let qt: ReturnType<typeof setTimeout>;
	$effect(() => {
		const v = q;
		clearTimeout(qt);
		qt = setTimeout(() => (qDebounced = v), 200);
	});

	let listErr = $state('');
	$effect(() => {
		conn.epoch;
		listEpoch;
		const p = new URLSearchParams();
		if (status) p.set('status', status);
		if (family) p.set('family', family);
		if (reviewed) p.set('reviewed', reviewed);
		if (qDebounced.trim()) p.set('q', qDebounced.trim());
		const s = p.toString();
		get<CallsResponse>('/api/calls' + (s ? '?' + s : ''))
			.then((r) => {
				list = r;
				listErr = '';
			})
			.catch((e) => (listErr = e.message));
	});

	let pt: ReturnType<typeof setTimeout>;
	function onThreshold() {
		clearTimeout(pt);
		pt = setTimeout(async () => {
			busy = true;
			try {
				const r = await put<SettingsPut>('/api/settings', { threshold: th });
				counts = r.counts;
				changed = r.changed;
				settings = r.settings;
				listEpoch++;
				get<Summary>('/api/summary').then((s) => (summary = s));
			} catch (e: any) {
				cutErr = e.message;
			} finally {
				busy = false;
			}
		}, 160);
	}

	// «How sure must a fact be?» (same setting as on the Advanced page): the plot's cutoff lines follow the slider
	// at once, the counts and the list after the re-decision
	let series = $derived(
		summary && meta
			? meta.models.fact_readers
					.filter((r) => summary!.fact_p_yes_histogram[r.id])
					.map((r) => ({ id: r.id, label: r.label, counts: summary!.fact_p_yes_histogram[r.id] }))
			: []
	);
	let ct: ReturnType<typeof setTimeout>;
	function onCertainty() {
		clearTimeout(ct);
		ct = setTimeout(async () => {
			busy = true;
			try {
				const r = await put<SettingsPut>('/api/settings', { certainty: cert });
				counts = r.counts;
				changed = r.changed;
				settings = r.settings;
				listEpoch++;
				get<Summary>('/api/summary').then((s) => (summary = s));
			} catch (e: any) {
				cutErr = e.message;
			} finally {
				busy = false;
			}
		}, 160);
	}
	function resetCertainty() {
		if (settings?.defaults.certainty == null) return;
		cert = settings.defaults.certainty;
		onCertainty();
	}

	function resetThreshold() {
		if (!settings) return;
		th = settings.defaults.threshold;
		onThreshold();
	}

	let cutErr = $state('');
	let band = $derived(settings?.review_band ?? 0.15);

	let total = $derived(counts ? counts.alarm + counts.review + counts.no_alert : 0);
	let changedMap = $derived(new Map(changed.map((x) => [x.id, x])));
	let reviewedCount = $derived(meta?.counts.reviewed);

	const tiles: { k: Label; flag: '' | 'flagged' | Label }[] = [
		{ k: 'alarm', flag: 'alarm' },
		{ k: 'review', flag: 'review' },
		{ k: 'no_alert', flag: 'no_alert' }
	];
</script>

<svelte:head><title>Calls · Sherlock Phones</title></svelte:head>

{#if demo && flaggedNoRule.length}
	<p class="small norule num">
		<b>Flagged without a rule:</b>
		{#each flaggedNoRule as c, i}<a href="/calls/{encodeURIComponent(c.id)}">{c.id}</a>{i < flaggedNoRule.length - 1 ? ', ' : ''}{/each}
	</p>
{/if}

<div class="grid body">
	<!-- 1. The three numbers + the alarm threshold -->
	<aside class="cut" aria-label="Outcome counts and alarm threshold">
		<div class="sticky">
			{#if sets.length > 1}
				<div class="sets" role="group" aria-label="Call set">
					{#each sets as cs}
						<button class="setb" class:on={cs.active} aria-pressed={cs.active} disabled={setBusy || cs.active} onclick={() => useSet(cs.id)}>{cs.id} <span class="num">{cs.calls}</span></button>
					{/each}
				</div>
			{/if}
			<p class="label">
				<span class="num">{total || '–'}</span> calls{#if reviewedCount !== undefined && conn.mode === 'live'}{' · '}<span class="num">{reviewedCount}</span> reviewed{/if}
			</p>
			<div class="tiles">
				{#each tiles as t}
					<button
						class="tile"
						class:sel={status === t.flag}
						aria-pressed={status === t.flag}
						onclick={() => (status = status === t.flag ? '' : t.flag)}
					>
						<span class="big num {t.k}">{counts ? counts[t.k] : '–'}</span>
						<span class="tl"><span class="sq {SQ[t.k]}" aria-hidden="true"></span>{LABEL[t.k]}</span>
					</button>
				{/each}
			</div>

			<div class="thr">
				<h2 id="cut-h" class="h3">Alarm threshold</h2>
				<div class="cval">
					<span class="display num">{th.toFixed(2)}</span>
					{#if settings && Math.abs(th - settings.defaults.threshold) > 1e-9}
						<button class="btn link small" onclick={resetThreshold}>Default {settings.defaults.threshold.toFixed(2)}</button>
					{/if}
				</div>
				<label class="sr-only" for="th">Alarm threshold</label>
				<input
					id="th"
					type="range"
					min={settings?.options.threshold.min ?? 0.05}
					max={settings?.options.threshold.max ?? 0.95}
					step={settings?.options.threshold.step ?? 0.01}
					bind:value={th}
					oninput={onThreshold}
					aria-valuetext={th.toFixed(2)}
				/>
				<p class="small muted num">
					Score ≥ {th.toFixed(2)} → <span class="o-alarm">Alarm</span> · ≥ {Math.max(0, th - band).toFixed(2)} → Review
				</p>
				{#if cutErr}<p class="small red">{cutErr}</p>{/if}
			</div>

			<div class="changes" aria-live="polite">
				{#if busy}
					<p class="small muted">Re-deciding…</p>
				{:else if changed.length}
					<p class="label">{changed.length} {changed.length === 1 ? 'call' : 'calls'} changed</p>
					<ul class="small num">
						{#each changed.slice(0, 8) as ch}
							<li><a href="/calls/{encodeURIComponent(ch.id)}">{ch.id}</a> <span class={O[ch.before]}>{LABEL[ch.before]}</span> → <span class={O[ch.after]}>{LABEL[ch.after]}</span></li>
						{/each}
					</ul>
				{/if}
			</div>

			{#if settings && settings.certainty != null}
				<div class="thr cert">
					<h2 class="h3">How sure must a fact be?</h2>
					<div class="cval">
						<span class="display num">{cert.toFixed(2)}</span>
						{#if settings.defaults.certainty != null && Math.abs(cert - settings.defaults.certainty) > 1e-9}
							<button class="btn link small" onclick={resetCertainty}>Default {settings.defaults.certainty.toFixed(2)}</button>
						{/if}
					</div>
					<label class="sr-only" for="cc">Certainty cutoff</label>
					<input
						id="cc"
						type="range"
						min={settings.options.certainty.min}
						max={settings.options.certainty.max}
						step={settings.options.certainty.step}
						bind:value={cert}
						oninput={onCertainty}
						aria-valuetext={cert.toFixed(2)}
					/>
					{#if summary && series.length}
						<div class="spread"><Spread edges={summary.fact_p_yes_histogram.edges} {series} c={cert} /></div>
						<p class="small num">{summary.facts.unclear} of {summary.facts.answered} fact answers unclear</p>
					{/if}
				</div>
			{/if}
		</div>
	</aside>

	<!-- 3. The list -->
	<section class="list" aria-labelledby="list-h">
		<h2 id="list-h" class="sr-only">Calls</h2>
		<div class="filters">
			<div class="search">
				<label class="label" for="q">Search</label>
				<input id="q" class="field" type="search" placeholder="Search calls or transcript" bind:value={q} />
			</div>
			<div>
				<label class="label" for="fam">Category</label>
				<select id="fam" class="field" bind:value={family}>
					<option value="">All categories</option>
					{#each meta?.families ?? [] as f}
						<option value={f.id}>{f.label}</option>
					{/each}
				</select>
			</div>
			<div>
				<span class="label" id="rv">Status</span>
				<div class="seg" role="radiogroup" aria-labelledby="rv">
					<label><input type="radio" bind:group={reviewed} value="" /><span>All</span></label>
					<label><input type="radio" bind:group={reviewed} value="false" /><span>Open</span></label>
					<label><input type="radio" bind:group={reviewed} value="true" /><span>Reviewed</span></label>
				</div>
			</div>
		</div>

		<div class="meta small muted num">
			{#if list}
				{list.calls.length} {list.calls.length === 1 ? 'call' : 'calls'}{status ? ` · ${status === 'flagged' ? 'flagged' : LABEL[status]}` : ''}, riskiest first
				{#if status || family || reviewed || q}
					<button class="btn link small" onclick={() => { status = ''; family = ''; reviewed = ''; q = ''; }}>Clear filters</button>
				{/if}
			{/if}
		</div>

		<table class="calls">
			<thead>
				<tr>
					<th scope="col" class="c-l">Outcome</th>
					<th scope="col" class="c-id">Call</th>
					<th scope="col">Why</th>
					<th scope="col" class="c-n">Length</th>
					<th scope="col" class="c-r">Reviewed</th>
				</tr>
			</thead>
			<tbody>
				{#each list?.calls ?? [] as call (call.id)}
					{@const ch = changedMap.get(call.id)}
					<tr onclick={() => goto(`/calls/${encodeURIComponent(call.id)}`)} class={call.label}>
						<td class="c-l">
							<span class="sq {SQ[call.label]}" aria-hidden="true"></span><span class={O[call.label]}>{LABEL[call.label]}</span>
							{#if ch}<span class="was small">was {LABEL[ch.before]}</span>{/if}
						</td>
						<td class="c-id num"><a href="/calls/{encodeURIComponent(call.id)}" onclick={(e) => e.stopPropagation()}>{call.id}</a></td>
						<td class="why">
							{#if call.family_label && call.label !== 'no_alert'}<span class="fam">{call.family_label}</span>{/if}
							<span class="reason">{stripRule(call.reason, call.family_label)}</span>
						</td>
						<td class="c-n num muted">{time(call.duration)}</td>
						<td class="c-r">{#if call.reviewed}<span aria-label="reviewed">✓</span>{:else}<span class="sr-only">open</span>{/if}</td>
					</tr>
				{:else}
					<tr><td colspan="5" class="empty muted">{list ? 'No calls match.' : listErr || 'Loading…'}</td></tr>
				{/each}
			</tbody>
		</table>
	</section>
</div>

<style>
	.norule {
		margin-bottom: 16px;
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 12px;
		margin-top: 8px;
		border-bottom: var(--rule-thick);
		padding-bottom: 12px;
	}
	.tile {
		text-align: left;
		background: none;
		border: 0;
		padding: 0 0 6px 0;
		cursor: pointer;
		border-bottom: 4px solid transparent;
	}
	.tile:hover {
		border-bottom-color: var(--grey-2);
	}
	.tile.sel {
		border-bottom-color: var(--black);
	}
	.big {
		display: block;
		font-size: 72px;
		font-weight: 700;
		letter-spacing: -0.04em;
		line-height: 1;
	}
	.big.alarm {
		color: var(--red);
	}
	.big.no_alert {
		color: var(--grey-3);
	}
	.tl {
		display: block;
		margin-top: 6px;
		font-weight: 600;
		font-size: var(--t-m);
		white-space: nowrap;
	}
	.thr {
		margin-top: 20px;
	}
	.thr .display {
		font-size: 64px;
	}
	.sets {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-bottom: 20px;
	}
	.setb {
		font: inherit;
		font-weight: 600;
		padding: 8px 14px;
		border: 2px solid #000;
		background: #fff;
		color: #000;
		cursor: pointer;
	}
	.setb.on {
		background: #000;
		color: #fff;
		cursor: default;
	}
	.setb:disabled:not(.on) {
		opacity: 0.5;
	}
	.setb .num {
		opacity: 0.7;
		margin-left: 4px;
	}
	.cert .display {
		font-size: 40px;
	}
	.spread {
		margin-top: 12px;
	}
	.body {
		align-items: start;
	}

	.cut {
		grid-column: 1 / span 4;
	}
	.sticky {
		position: sticky;
		top: calc(var(--head-h, 104px) + 24px);
	}
	.cval {
		display: flex;
		align-items: baseline;
		gap: 16px;
		margin-top: 4px;
	}
	.changes {
		margin-top: 16px;
		min-height: 24px;
	}
	.changes ul {
		margin-top: 8px;
	}
	.changes li {
		padding: 4px 0;
		border-bottom: var(--hair);
	}

	.list {
		grid-column: 6 / span 7;
	}
	.filters {
		display: grid;
		grid-template-columns: 1.4fr 1fr auto;
		gap: 24px;
		align-items: start;
	}
	.filters .label {
		display: block;
		margin-bottom: 4px;
	}
	.meta {
		margin-top: 24px;
		display: flex;
		gap: 16px;
		align-items: baseline;
	}

	.calls {
		width: 100%;
		border-collapse: collapse;
		margin-top: 8px;
	}
	.calls th {
		text-align: left;
		font-size: var(--t-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		padding: 8px 12px 8px 0;
		border-bottom: var(--rule);
	}
	.calls td {
		padding: 10px 12px 10px 0;
		border-bottom: var(--hair);
		vertical-align: top;
	}
	.calls tbody tr {
		cursor: pointer;
	}
	.calls tbody tr:hover td {
		background: var(--grey-1);
	}
	.calls tr.alarm td:first-child {
		box-shadow: inset 4px 0 0 var(--red);
		padding-left: 12px;
	}
	.calls td:first-child,
	.calls th:first-child {
		padding-left: 12px;
	}
	.c-l {
		white-space: nowrap;
		width: 1%;
	}
	.c-id {
		white-space: nowrap;
		font-weight: 600;
		width: 1%;
	}
	.c-n,
	.c-r {
		text-align: right;
		white-space: nowrap;
		width: 1%;
	}
	.why .fam {
		display: block;
		font-weight: 600;
	}
	.why .reason {
		display: block;
		font-size: var(--t-s);
		color: var(--grey-ink);
		max-width: 60ch;
	}
	.was {
		display: block;
		color: var(--grey-ink);
		margin-left: 18px;
	}
	.empty {
		padding: 32px 0;
	}

	@media (max-width: 1100px) {
		.cut,
		.list {
			grid-column: 1 / span 12;
		}
		.list {
			margin-top: 48px;
		}
		.filters {
			grid-template-columns: 1fr;
		}
	}
</style>
