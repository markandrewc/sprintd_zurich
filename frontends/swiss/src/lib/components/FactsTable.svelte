<script lang="ts">
	import type { FactAnswer, FactValue, Reader } from '#lib/types.ts';

	interface Props {
		family: string;
		label: string;
		decided: boolean;
		facts: FactAnswer[];
		readers: Reader[];
		corrections: Record<string, FactValue>;
		onEvidence: (ids: string[]) => void;
		/** open at start although no rule of this category decided (e.g. the empty demo rule book) */
		startOpen?: boolean;
	}
	let { family, label, decided, facts, readers, corrections = $bindable(), onEvidence, startOpen = false }: Props = $props();

	let open = $state(false);
	let shown = $state<string | null>(null);
	$effect(() => {
		open = decided || startOpen;
	});

	const V: Record<string, string> = { yes: 'Yes', no: 'No', unclear: 'Unclear' };
	let yesCount = $derived(facts.filter((f) => f.resolved === 'yes').length);

	function setCorr(key: string, v: string) {
		const next = { ...corrections };
		if (!v) delete next[key];
		else next[key] = v as FactValue;
		corrections = next;
	}
</script>

<div class="fam" class:decided>
	<button class="fh" onclick={() => (open = !open)} aria-expanded={open}>
		<span class="h3">{label}</span>
		<span class="small muted num">{yesCount}/{facts.length} yes</span>
		<span class="chev" aria-hidden="true">{open ? '−' : '+'}</span>
	</button>
	{#if open}
		<ul>
			{#each facts as f (f.id)}
				{@const key = `${family}.${f.id}`}
				<li>
					<div class="row1">
						<div>
							<p class="fl" title={f.question}>{f.label}</p>
						</div>
						<p class="val {f.resolved}">{V[f.resolved] ?? f.resolved}</p>
					</div>
					<div class="readers">
						{#each readers as r}
							{@const a = f.readers[r.id]}
							<div class="rd">
								<span class="rn">{r.label}</span>
								{#if a}
									<span class="pbar" aria-hidden="true"><span style="width:{a.p_yes * 100}%" class={a.value}></span></span>
									<span class="pv num">{a.p_yes.toFixed(2)}</span>
								{:else}
									<span class="small muted">no answer</span>
								{/if}
							</div>
						{/each}
						<span class="agree small" class:dis={!f.agree}>{f.agree ? 'Agree' : 'Disagree'}</span>
					</div>
					<div class="row3 small">
						<button
							class="btn link small"
							aria-expanded={shown === f.id}
							onclick={() => {
								shown = shown === f.id ? null : f.id;
								if (shown && f.evidence_segment_ids?.length) onEvidence(f.evidence_segment_ids);
							}}>{f.evidence_segment_ids?.length ? 'Evidence' : 'Question'}</button
						>
						<label class="corr">
							<span class="muted">Correct:</span>
							<select
								value={corrections[key] ?? ''}
								onchange={(e) => setCorr(key, (e.currentTarget as HTMLSelectElement).value)}
								aria-label="Your answer for {f.label}"
								class:set={corrections[key]}
							>
								<option value="">–</option>
								<option value="yes">yes</option>
								<option value="no">no</option>
								<option value="unclear">unclear</option>
							</select>
						</label>
					</div>
					{#if shown === f.id}
						<p class="q small muted">{f.question}</p>
						{#if f.evidence_reason}<blockquote class="small">{f.evidence_reason}</blockquote>{/if}
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.fam {
		border-top: var(--rule);
	}
	.fam.decided {
		border-top: 4px solid var(--red);
	}
	.fh {
		display: grid;
		grid-template-columns: 1fr auto 24px;
		gap: 12px;
		align-items: baseline;
		width: 100%;
		background: none;
		border: 0;
		padding: 12px 0;
		text-align: left;
		cursor: pointer;
	}
	.chev {
		font-size: 20px;
		text-align: right;
		line-height: 1;
	}
	ul {
		padding-bottom: 16px;
	}
	li {
		padding: 12px 0 14px;
		border-top: var(--hair);
	}
	.row1 {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 16px;
	}
	.fl {
		font-weight: 600;
	}
	.q {
		margin-top: 2px;
	}
	.val {
		font-weight: 700;
		font-size: var(--t-s);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.val.no {
		color: var(--grey-ink);
		font-weight: 500;
	}
	.val.unclear {
		color: var(--red-ink);
	}
	.readers {
		display: grid;
		grid-template-columns: 1fr 1fr auto;
		gap: 16px;
		margin-top: 10px;
		align-items: center;
	}
	.rd {
		display: grid;
		grid-template-columns: 36px 1fr 34px;
		gap: 6px;
		align-items: center;
	}
	.rn {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	.pbar {
		height: 8px;
		background: var(--grey-1);
		position: relative;
	}
	.pbar span {
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		background: var(--black);
	}
	.pbar span.unclear {
		background: var(--red);
	}
	.pbar span.no {
		background: var(--grey-3);
	}
	.pv {
		font-size: var(--t-xs);
		text-align: right;
	}
	.agree {
		font-size: var(--t-xs);
		font-weight: 600;
	}
	.agree.dis {
		color: var(--red-ink);
	}
	.row3 {
		display: flex;
		gap: 16px;
		align-items: center;
		margin-top: 8px;
		font-size: var(--t-xs);
	}
	blockquote {
		margin: 10px 0 0;
		padding-left: 12px;
		border-left: 3px solid var(--black);
		font-size: var(--t-xs);
	}
	.corr {
		margin-left: auto;
		display: inline-flex;
		gap: 6px;
		align-items: center;
	}
	.corr select {
		border: 0;
		border-bottom: 1px solid var(--black);
		background: none;
		font-size: var(--t-xs);
		padding: 2px 0;
	}
	.corr select.set {
		color: var(--red-ink);
		font-weight: 700;
		border-bottom-color: var(--red);
	}
</style>
