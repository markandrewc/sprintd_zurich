<script lang="ts">
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { get, post, conn, setUser, bump } from '#lib/api.svelte.ts';
	import { LABEL, O, time, p2 } from '#lib/format.ts';
	import type { CallDetail, CallRow, CallsResponse, Family, FactValue, ReviewBody, ReviewSaved } from '#lib/types.ts';

	interface Props {
		call: CallDetail;
		corrections: Record<string, FactValue>;
		families: Family[];
	}
	let { call, corrections, families }: Props = $props();

	let verdict = $state<ReviewBody['verdict'] | ''>('');
	let agree = $state<'' | 'yes' | 'no'>('');
	let reasons = $state<string[]>([]);
	let missed = $state('');
	let passageOk = $state<Record<string, boolean>>({});
	let comment = $state('');
	let name = $state(conn.user);
	let saving = $state(false);
	let saved = $state<ReviewSaved | null>(null);
	let error = $state('');

	const REASONS = [
		{ id: 'context_harmless', t: 'Harmless in context' },
		{ id: 'transcript_error', t: 'Transcript is wrong' },
		{ id: 'rule_too_strict', t: 'Rule too strict' },
		{ id: 'rule_too_lax', t: 'Rule too lax' },
		{ id: 'missing_info', t: 'Information missing' },
		{ id: 'other_family', t: 'Wrong or missed category' }
	];

	let label = $derived(call.decision.label);
	let nCorr = $derived(Object.keys(corrections).length);
	let canSave = $derived(!!verdict && !!agree && !!name.trim() && !saving);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (!canSave) return;
		saving = true;
		error = '';
		setUser(name.trim());
		const missedLabel = families.find((f) => f.id === missed)?.label;
		const body: ReviewBody = {
			verdict: verdict as ReviewBody['verdict'],
			agree: agree === 'yes',
			reasons: missed && !reasons.includes('other_family') ? [...reasons, 'other_family'] : reasons,
			fact_corrections: corrections,
			passage_ok: Object.fromEntries(Object.entries(passageOk).map(([k, v]) => [k, v])),
			comment: [missedLabel ? `Missed category: ${missedLabel}.` : '', comment.trim()].filter(Boolean).join(' '),
			reviewer: name.trim()
		};
		try {
			saved = await post<ReviewSaved>(`/api/calls/${encodeURIComponent(call.id)}/review`, body);
			bump();
			findNext();
		} catch (err: any) {
			error = err.message ?? 'Could not save.';
		} finally {
			saving = false;
		}
	}

	function again() {
		saved = null;
	}

	// ---------- next case: the riskiest flagged call nobody has reviewed yet ----------
	let next = $state<CallRow | null | undefined>(undefined); // undefined while looking
	let openLeft = $state(0);
	let nextBtn = $state<HTMLButtonElement | null>(null);
	let savedEl = $state<HTMLElement | null>(null);

	async function findNext() {
		next = undefined;
		try {
			const r = await get<CallsResponse>('/api/calls?status=flagged&reviewed=false');
			const open = r.calls.filter((c) => c.id !== call.id && !c.reviewed);
			openLeft = open.length;
			next = open[0] ?? null;
		} catch {
			next = null;
		}
		await tick();
		savedEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
		nextBtn?.focus({ preventScroll: true });
	}

	function goNext() {
		if (next) goto(`/calls/${encodeURIComponent(next.id)}`);
	}
</script>

<section class="review" aria-labelledby="rv-h">
	<h2 id="rv-h" class="h1">Review</h2>

	{#if saved}
		<div class="saved" role="status" bind:this={savedEl}>
			<p class="h2">Saved.</p>
		</div>
		<div class="next">
			{#if next === undefined}
				<p class="label muted">Finding the next case…</p>
			{:else if next}
				<p class="label">Next case <span class="muted num">· {openLeft} flagged {openLeft === 1 ? 'call' : 'calls'} still open</span></p>
				<button class="btn primary big" bind:this={nextBtn} onclick={goNext}>
					<span class="num">{next.id}</span><span aria-hidden="true">→</span>
				</button>
				<p class="small muted num">
					<span class={O[next.label]}>{LABEL[next.label]}</span> · {[next.family_label, `score ${p2(next.score)}`, time(next.duration)].filter(Boolean).join(' · ')}
				</p>
			{:else}
				<p class="label">All flagged calls are reviewed.</p>
				<a class="btn primary big" href="/">Back to all calls</a>
			{/if}
			<button class="btn link small" onclick={again}>Add another review</button>
		</div>
	{:else}
		<form onsubmit={submit}>
			<fieldset>
				<legend class="step"><span class="sn">1</span>Verdict</legend>
				<div class="choices">
					{#each [['violation', 'Violation confirmed'], ['no_violation', 'No violation'], ['unclear', 'Unclear']] as [v, t]}
						<label class="choice" class:on={verdict === v}>
							<input type="radio" name="verdict" value={v} bind:group={verdict} />
							<span>{t}</span>
						</label>
					{/each}
				</div>
			</fieldset>

			<fieldset>
				<legend class="step"><span class="sn">2</span><span>The system said <span class={O[label]}>{LABEL[label]}</span>.</span></legend>
				<div class="choices two">
					<label class="choice" class:on={agree === 'yes'}>
						<input type="radio" name="agree" value="yes" bind:group={agree} />
						<span>Agree</span>
					</label>
					<label class="choice" class:on={agree === 'no'}>
						<input type="radio" name="agree" value="no" bind:group={agree} />
						<span>Disagree</span>
					</label>
				</div>
			</fieldset>

			<fieldset>
				<legend class="step"><span class="sn">3</span>Why <span class="opt">optional</span></legend>
				<div class="reasons">
					{#each REASONS as r}
						<label class="check">
							<input type="checkbox" value={r.id} bind:group={reasons} />
							<span>{r.t}</span>
						</label>
					{/each}
				</div>
				{#if reasons.includes('other_family')}
					<label class="sub">
						<span class="label">Category it should have been</span>
						<select class="field" bind:value={missed}>
							<option value="">Choose…</option>
							{#each families as f}<option value={f.id}>{f.label}</option>{/each}
						</select>
					</label>
				{/if}

				{#if call.passages.length}
					<p class="label sub">Passages</p>
					<ul class="pass">
						{#each call.passages as p, i}
							<li>
								<span><b>P{i + 1}</b> <span class="num muted">{time(p.start)}</span> {p.family_label}</span>
								<span class="seg">
									<label><input type="radio" name="p{i}" checked={passageOk[i] === true} onchange={() => (passageOk = { ...passageOk, [i]: true })} /><span>Applies</span></label>
									<label><input type="radio" name="p{i}" checked={passageOk[i] === false} onchange={() => (passageOk = { ...passageOk, [i]: false })} /><span>Does not</span></label>
								</span>
							</li>
						{/each}
					</ul>
				{/if}

				{#if nCorr}
					<p class="small muted sub"><b>{nCorr}</b> fact {nCorr === 1 ? 'answer' : 'answers'} corrected above.</p>
				{/if}

				<label class="sub">
					<span class="label">Comment</span>
					<textarea class="field" bind:value={comment} rows="2"></textarea>
				</label>
			</fieldset>

			<fieldset>
				<legend class="step"><span class="sn">4</span>Sign</legend>
				<label>
					<span class="sr-only">Your name</span>
					<input class="field" bind:value={name} placeholder="Your name" required />
				</label>
			</fieldset>

			{#if error}<p class="red small" role="alert">{error}</p>{/if}
			<button class="btn primary big" type="submit" disabled={!canSave}>
				{saving ? 'Saving…' : 'Save review'}
			</button>
			{#if !canSave && !saving}
				<p class="small muted hint">Needs a verdict, agree or disagree, and your name.</p>
			{/if}
		</form>
	{/if}
</section>

<style>
	.review {
		margin-top: 64px;
		border-top: var(--rule-thick);
		padding-top: 16px;
	}
	.review .h1 {
		margin: 4px 0 24px;
	}
	fieldset {
		border: 0;
		padding: 0;
		margin: 0 0 32px;
	}
	.step {
		font-weight: 700;
		font-size: var(--t-m);
		margin-bottom: 12px;
		display: flex;
		gap: 12px;
		align-items: baseline;
		padding: 0;
	}
	.sn {
		font-size: var(--t-xs);
		width: 22px;
		height: 22px;
		display: inline-grid;
		place-items: center;
		background: var(--black);
		color: var(--white);
		flex: none;
	}
	.opt {
		font-weight: 400;
		font-size: var(--t-xs);
		color: var(--grey-ink);
	}
	.choices {
		display: grid;
		grid-template-columns: 1fr;
		border-top: var(--rule);
	}
	.choices.two {
		grid-template-columns: 1fr 1fr;
		border-top: 0;
		gap: 8px;
	}
	.choice {
		position: relative;
		display: block;
		cursor: pointer;
		border-bottom: var(--rule);
	}
	.choices.two .choice {
		border: 2px solid var(--black);
	}
	.choice input {
		position: absolute;
		opacity: 0;
	}
	.choice span {
		display: block;
		padding: 12px 12px;
		font-weight: 600;
	}
	.choice:hover span {
		background: var(--grey-1);
	}
	.choice.on span {
		background: var(--black);
		color: var(--white);
	}
	.choice input:focus-visible + span {
		outline: 3px solid var(--red);
		outline-offset: -3px;
	}
	.reasons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px 16px;
	}
	.check {
		display: flex;
		gap: 8px;
		align-items: center;
		font-size: var(--t-s);
		cursor: pointer;
	}
	.check input {
		width: 16px;
		height: 16px;
		accent-color: var(--black);
		margin: 0;
	}
	.sub {
		display: block;
		margin-top: 20px;
	}
	.pass li {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
		padding: 8px 0;
		border-bottom: var(--hair);
		font-size: var(--t-s);
	}
	.pass .seg span {
		padding: 4px 8px;
		font-size: var(--t-xs);
	}
	.big {
		width: 100%;
		justify-content: center;
		min-height: 56px;
		font-size: var(--t-m);
	}
	.hint {
		margin-top: 8px;
	}
	.saved {
		border-top: var(--rule);
		padding-top: 16px;
	}
	.next {
		margin-top: 32px;
		border-top: 4px solid var(--red);
		padding-top: 12px;
	}
	.next .big {
		margin: 12px 0 8px;
		justify-content: space-between;
	}
	.next .link {
		margin-top: 24px;
	}
</style>
