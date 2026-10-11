<script lang="ts">
	import { get, conn } from '#lib/api.svelte.ts';
	import PageHead from '#lib/components/PageHead.svelte';
	import type { Step } from '#lib/types.ts';

	let steps = $state<Step[]>([]);
	let err = $state('');
	$effect(() => {
		conn.epoch;
		get<{ steps: Step[] }>('/api/how-it-works')
			.then((d) => {
				steps = d.steps;
				err = '';
			})
			.catch((e) => (err = e.message));
	});

	// the API names each step's phase; this is only the fallback for an older API
	const PHASE: Record<string, string> = {
		audio: 'Listen',
		asr: 'Listen',
		diarization: 'Listen',
		keywords: 'Read',
		facts: 'Read',
		combine: 'Decide',
		rules: 'Decide',
		fusion: 'Decide',
		swiss_german: 'Display',
		review: 'Person'
	};
	const phaseOf = (s: Step) => s.phase ?? PHASE[s.id] ?? 'Decide';
	let phases = $derived.by(() => {
		const out: { name: string; steps: (Step & { n: number })[] }[] = [];
		steps.forEach((s, i) => {
			const name = phaseOf(s);
			const last = out.at(-1);
			if (last && last.name === name) last.steps.push({ ...s, n: i + 1 });
			else out.push({ name, steps: [{ ...s, n: i + 1 }] });
		});
		return out;
	});
	const display = (id: string) => id === 'swiss_german';
</script>

<svelte:head><title>How it works · Sherlock Phones</title></svelte:head>

<PageHead n="05" title="How it works" lead="From a phone call to a decision a person can check. Everything runs on the bank's own machines." />

{#if err}<p class="red">{err}</p>{/if}

<!-- the diagram: phases as columns, steps flow left to right -->
<figure class="flow" aria-label="Pipeline diagram">
	<div class="cols" style="grid-template-columns: {phases.map((p) => `${Math.max(p.steps.length, 1.6)}fr`).join(' ')}">
		{#each phases as ph, pi}
			<div class="ph" class:human={ph.name === 'Person'}>
				<p class="pn"><span class="num">{String.fromCharCode(65 + pi)}</span> {ph.name}</p>
				<ol>
					{#each ph.steps as s}
						<li class:side={display(s.id)} class:key={s.id === 'facts' || s.id === 'rules'}>
							<span class="sn num">{String(s.n).padStart(2, '0')}</span>
							<span class="st">{s.title}</span>
						</li>
					{/each}
				</ol>
			</div>
		{/each}
	</div>
	<div class="line" aria-hidden="true"><span></span></div>
	<figcaption class="small muted">Read left to right. Red: where the decision is made. Dashed: after the decision, for display only; no decision reads it.</figcaption>
</figure>

<!-- the details -->
<ol class="detail">
	{#each steps as s, i}
		<li class="grid" class:key={s.id === 'facts' || s.id === 'rules'}>
			<span class="dn num">{String(i + 1).padStart(2, '0')}</span>
			<div class="dt">
				<p class="label muted">{phaseOf(s)}</p>
				<h2 class="h2">{s.title}</h2>
			</div>
			<p class="dd">{s.description}</p>
			<p class="dm small">{#if s.model}<span class="label muted">Model</span><br />{s.model}{/if}</p>
		</li>
	{/each}
</ol>

<style>
	.flow {
		margin-top: 56px;
	}
	.cols {
		display: grid;
		gap: 0;
	}
	.ph {
		border-left: var(--rule);
		padding: 0 16px 0 12px;
	}
	.pn {
		font-size: var(--t-xl);
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-bottom: 24px;
	}
	.pn .num {
		color: var(--grey-3);
	}
	.ph.human .pn {
		color: var(--red);
	}
	.ph ol {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: 1fr;
		gap: 12px;
	}
	.ph li {
		border-top: 4px solid var(--black);
		padding-top: 10px;
		min-height: 120px;
	}
	.ph li.key {
		border-top-color: var(--red);
	}
	.ph li.side {
		border-top: 4px dashed var(--grey-3);
		color: var(--grey-ink);
	}
	.sn {
		display: block;
		font-size: var(--t-xs);
		font-weight: 600;
		color: var(--grey-ink);
	}
	.st {
		display: block;
		font-weight: 700;
		font-size: var(--t-m);
		line-height: 1.2;
		margin-top: 4px;
		hyphens: auto;
	}
	.line {
		height: 0;
		border-top: var(--rule);
		position: relative;
		margin-top: 8px;
	}
	.line span {
		position: absolute;
		right: -2px;
		top: -7px;
		border-left: 12px solid var(--black);
		border-top: 6px solid transparent;
		border-bottom: 6px solid transparent;
	}
	figcaption {
		margin-top: 12px;
	}

	.detail {
		margin-top: 96px;
		border-top: var(--rule-thick);
	}
	.detail li {
		padding: 20px 0 24px;
		border-bottom: var(--hair);
		align-items: start;
	}
	.dn {
		grid-column: 1 / span 1;
		font-size: var(--t-xxl);
		font-weight: 700;
		letter-spacing: -0.04em;
		line-height: 1;
	}
	.key .dn {
		color: var(--red);
	}
	.dt {
		grid-column: 2 / span 3;
	}
	.dd {
		grid-column: 5 / span 5;
		font-size: var(--t-l);
		line-height: 1.4;
	}
	.dm {
		grid-column: 10 / span 3;
		word-break: break-word;
	}
	@media (max-width: 1100px) {
		.cols {
			grid-template-columns: 1fr !important;
		}
		.ph {
			margin-bottom: 24px;
		}
		.dt,
		.dd,
		.dm {
			grid-column: 2 / span 11;
		}
	}
</style>
