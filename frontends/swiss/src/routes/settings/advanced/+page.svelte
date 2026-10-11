<script lang="ts">
	import { get, put, conn, bump } from '#lib/api.svelte.ts';
	import { LABEL, O } from '#lib/format.ts';
	import PageHead from '#lib/components/PageHead.svelte';
	import Spread from '#lib/components/Spread.svelte';
	import type { Meta, Settings, SettingsPut, Summary } from '#lib/types.ts';

	let s = $state<Settings | null>(null);
	let certainty = $state(0.6);
	let combination = $state('agree');
	let onSplit = $state('rules');
	let res = $state<SettingsPut | null>(null);
	let summary = $state<Summary | null>(null);
	let meta = $state<Meta | null>(null);

	$effect(() => {
		conn.epoch;
		get<Settings>('/api/settings').then((x) => {
			s = x;
			certainty = x.certainty ?? 0.6;
			combination = x.combination ?? '';
			onSplit = x.on_split ?? '';
		});
		get<Meta>('/api/meta').then((m) => (meta = m)).catch(() => {});
		loadSummary();
	});
	function loadSummary() {
		get<Summary>('/api/summary').then((x) => (summary = x)).catch(() => {});
	}
	let hasCutoff = $derived(s ? s.certainty != null : true);
	let series = $derived(
		summary && meta
			? meta.models.fact_readers
					.filter((r) => summary!.fact_p_yes_histogram[r.id])
					.map((r) => ({ id: r.id, label: r.label, counts: summary!.fact_p_yes_histogram[r.id] }))
			: []
	);

	let t: ReturnType<typeof setTimeout>;
	function send(body: Record<string, unknown>) {
		clearTimeout(t);
		t = setTimeout(async () => {
			try {
				res = await put<SettingsPut>('/api/settings', body);
				s = res.settings;
				err = '';
				loadSummary();
			} catch (e: any) {
				err = e.message;
			}
		}, 150);
	}

	let err = $state('');
	async function reset() {
		try {
			res = await put<SettingsPut>('/api/settings', { reset: true });
		} catch (e: any) {
			err = e.message;
			return;
		}
		s = res.settings;
		certainty = s.certainty ?? 0.6;
		combination = s.combination ?? '';
		onSplit = s.on_split ?? '';
		bump();
	}
</script>

<svelte:head><title>Advanced · Sherlock Phones</title></svelte:head>

<PageHead n="" title="Advanced">
	<button class="btn" onclick={reset}>Back to defaults</button>
</PageHead>

<div class="grid adv">
	<section class="k">
		<p class="label muted">How sure must a fact be?</p>
		{#if !hasCutoff}
			<p class="small muted">Not available for this profile.</p>
		{:else}
			<p class="display num">{certainty.toFixed(2)}</p>
			<label class="sr-only" for="cc">Certainty cutoff</label>
			<input id="cc" type="range" min={s?.options.certainty.min ?? 0.5} max={s?.options.certainty.max ?? 1} step={s?.options.certainty.step ?? 0.01} bind:value={certainty} oninput={() => send({ certainty })} />
			<div class="scale small muted"><span>lenient</span><span>strict</span></div>
			<p class="small muted">A reader's answer counts as yes or no only this sure; otherwise unclear. Default {s?.defaults.certainty?.toFixed(2) ?? '–'}. The alarm threshold is on <a href="/">Calls</a>.</p>
			{#if summary && series.length}
				<div class="spread"><Spread edges={summary.fact_p_yes_histogram.edges} {series} c={certainty} /></div>
				<p class="small num">{summary.facts.unclear} of {summary.facts.answered} fact answers unclear</p>
			{/if}
		{/if}
	</section>

	<section class="k">
		<p class="label muted">Combine the two readers</p>
		<ol class="opts">
			{#if s && !s.options.combination.length}
				<li class="small muted">Not available for this profile.</li>
			{/if}
			{#each s?.options.combination ?? [] as o}
				<li>
					<label class:on={combination === o.id}>
						<input type="radio" name="comb" value={o.id} bind:group={combination} onchange={() => send({ combination })} />
						<span class="h3">{o.label}</span>
						<span class="small muted">{o.help}</span>
					</label>
				</li>
			{/each}
		</ol>
	</section>

	<section class="k">
		<p class="label muted">When Qwen and Kev disagree</p>
		<ol class="opts">
			{#if s && !(s.options.on_split ?? []).length}
				<li class="small muted">Not available for this profile.</li>
			{/if}
			{#each s?.options.on_split ?? [] as o}
				<li>
					<label class:on={onSplit === o.id}>
						<input type="radio" name="split" value={o.id} bind:group={onSplit} onchange={() => send({ on_split: onSplit })} />
						<span class="h3">{o.label}</span>
						<span class="small muted">{o.help}</span>
					</label>
				</li>
			{/each}
		</ol>
	</section>

	<section class="k res" class:empty={!res && !err} aria-live="polite">
		<p class="label muted">Result</p>
		{#if err}<p class="small red">{err}</p>{/if}
		{#if res}
			<p class="h2 num"><span class="o-alarm">{res.counts.alarm}</span> · {res.counts.review} · <span class="o-none">{res.counts.no_alert}</span></p>
			<p class="small muted">alarm · review · no alert</p>
			{#if res.changed.length}
				<ul class="small num">
					{#each res.changed.slice(0, 10) as c}
						<li><a href="/calls/{encodeURIComponent(c.id)}">{c.id}</a> <span class={O[c.before]}>{LABEL[c.before]}</span> → <span class={O[c.after]}>{LABEL[c.after]}</span></li>
					{/each}
				</ul>
			{/if}
		{/if}
	</section>
</div>

<style>
	.adv {
		margin-top: 48px;
		align-items: start;
	}
	.k {
		grid-column: span 4;
		border-top: var(--rule);
		padding-top: 12px;
	}
	.k .display {
		margin: 8px 0;
	}
	.opts {
		margin-top: 8px;
	}
	.scale {
		display: flex;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.spread {
		margin-top: 24px;
	}
	.opts label {
		display: block;
		padding: 12px 12px;
		border-bottom: var(--hair);
		cursor: pointer;
		position: relative;
	}
	.opts input {
		position: absolute;
		opacity: 0;
	}
	.opts label.on {
		box-shadow: inset 4px 0 0 var(--red);
	}
	.opts label:has(input:focus-visible) {
		outline: 3px solid var(--red);
	}
	.opts span {
		display: block;
	}
	.res.empty {
		visibility: hidden;
	}
	.res ul {
		margin-top: 12px;
	}
	.res li {
		padding: 3px 0;
		border-bottom: var(--hair);
	}
	@media (max-width: 1100px) {
		.k {
			grid-column: span 12;
			margin-top: 24px;
		}
	}
</style>
