<script lang="ts">
	import { page } from '$app/state';
	import { onDestroy, tick } from 'svelte';
	import { get, conn, audioSrc } from '#lib/api.svelte.ts';
	import { LABEL, O, SQ, time, stripRule, role, p2 } from '#lib/format.ts';
	import { Clock } from '#lib/clock.svelte.ts';
	import FactsTable from '#lib/components/FactsTable.svelte';
	import ReviewForm from '#lib/components/ReviewForm.svelte';
	import Condition, { factsOf } from '#lib/components/Condition.svelte';
	import type { CallDetail, Meta, Segment, FactValue, FactAnswer, PassageSource } from '#lib/types.ts';

	let id = $derived(decodeURIComponent(page.params.id ?? ''));
	let call = $state<CallDetail | null>(null);
	let meta = $state<Meta | null>(null);
	let err = $state('');

	const clock = new Clock();
	onDestroy(() => clock.destroy());

	$effect(() => {
		conn.epoch;
		const cid = id;
		err = '';
		get<CallDetail>(`/api/calls/${encodeURIComponent(cid)}`)
			.then((d) => {
				call = d;
				clock.duration = d.duration || (d.segments.at(-1)?.end ?? 0);
			})
			.catch((e) => (err = e.message));
		get<Meta>('/api/meta').then((m) => (meta = m));
	});

	// ---------- audio ----------
	let audioEl = $state<HTMLAudioElement | null>(null);
	let src = $derived(call && call.has_audio !== false ? audioSrc(call.audio_url) : null);
	$effect(() => {
		clock.attach(audioEl);
		clock.audio = !!(audioEl && src);
	});

	// ---------- transcript ----------
	let view = $state<'de' | 'gsw'>('de');
	let segs = $derived.by<Segment[]>(() => {
		if (!call) return [];
		if (view === 'gsw' && call.swiss_german) {
			const m = new Map(call.swiss_german.segments.map((s) => [s.id, s.text]));
			return call.segments.map((s) => ({ ...s, text: m.get(s.id) ?? s.text }));
		}
		return call.segments;
	});

	let active = $derived.by(() => {
		let a = -1;
		for (let i = 0; i < segs.length; i++) {
			if (segs[i].start <= clock.t + 0.05) a = i;
			else break;
		}
		return a;
	});

	// segment id -> passage index (1-based label)
	let passageOf = $derived.by(() => {
		const m = new Map<string, number>();
		call?.passages.forEach((p, i) => p.segment_ids.forEach((s) => m.has(s) || m.set(s, i)));
		return m;
	});
	let passageStart = $derived.by(() => {
		const s = new Set<string>();
		call?.passages.forEach((p) => p.segment_ids[0] && s.add(p.segment_ids[0]));
		return s;
	});
	let hitsBySeg = $derived.by(() => {
		const m = new Map<string, string[]>();
		call?.keyword_hits.forEach((h) =>
			h.segment_ids.forEach((s) => m.set(s, [...(m.get(s) ?? []), h.phrase]))
		);
		return m;
	});
	let evidence = $state<Set<string>>(new Set());

	let box = $state<HTMLElement | null>(null);
	let follow = $state(true);

	$effect(() => {
		const i = active;
		if (!follow || i < 0 || !box) return;
		const el = box.querySelector<HTMLElement>(`[data-i="${i}"]`);
		if (!el) return;
		box.scrollTo({ top: el.offsetTop - box.clientHeight * 0.3, behavior: 'smooth' });
	});

	function userScrolled() {
		if (clock.playing) follow = false;
	}

	function seekTo(s: number, play = true) {
		clock.seek(s);
		follow = true;
		if (play) clock.play();
	}

	/** Play exactly this passage (start to end); a second click on the playing passage pauses. */
	function playPassage(i: number) {
		const p = call?.passages[i];
		if (!p) return;
		if (playingPassage === i) {
			clock.pause();
			return;
		}
		follow = true;
		clock.playRange(p.start, p.end);
	}
	let playingPassage = $derived.by(() => {
		if (!call || !clock.playing || clock.stopAt === null) return -1;
		return call.passages.findIndex((p) => p.end === clock.stopAt);
	});

	function showEvidence(ids: string[]) {
		evidence = new Set(ids);
		const s = call?.segments.find((x) => x.id === ids[0]);
		if (s) seekTo(Math.max(0, s.start - 1), false);
	}

	function nextPassage(dir = 1) {
		if (!call?.passages.length) return;
		const ps = call.passages;
		let i = dir > 0 ? ps.findIndex((p) => p.start > clock.t + 0.5) : ps.findLastIndex((p) => p.start < clock.t - 1);
		if (i < 0) i = dir > 0 ? 0 : ps.length - 1;
		playPassage(i);
	}

	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement;
		if (t.closest('input, textarea, select, [contenteditable]')) return;
		if (e.key === ' ' && !t.closest('button, a')) {
			e.preventDefault();
			clock.toggle();
		} else if (e.key === 'ArrowLeft' && !t.closest('[role=slider], input')) {
			clock.seek(clock.t - 5);
		} else if (e.key === 'ArrowRight' && !t.closest('[role=slider], input')) {
			clock.seek(clock.t + 5);
		} else if (e.key === 'n') {
			nextPassage(1);
		} else if (e.key === 'p') {
			nextPassage(-1);
		}
	}

	// timeline click
	function onBar(e: MouseEvent) {
		const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
		seekTo(((e.clientX - r.left) / r.width) * clock.duration, clock.playing);
	}
	function onBarKey(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft') clock.seek(clock.t - 5);
		else if (e.key === 'ArrowRight') clock.seek(clock.t + 5);
		else return;
		e.preventDefault();
		e.stopPropagation();
	}

	function highlight(text: string, phrases: string[] | undefined): { t: string; hit: boolean }[] {
		if (!phrases?.length || view !== 'de') return [{ t: text, hit: false }];
		const esc = phrases.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
		const re = new RegExp(`(${esc})`, 'gi');
		return text.split(re).filter(Boolean).map((t) => ({ t, hit: re.test(t) && (re.lastIndex = 0, true) }));
	}

	// officer corrections, filled from the facts table
	let corrections = $state<Record<string, FactValue>>({});

	let decided = $derived(call?.decision.family ?? null);
	let familyOrder = $derived.by(() => {
		if (!call) return [];
		const ids = Object.keys(call.facts);
		return ids.sort((a, b) => (a === decided ? -1 : b === decided ? 1 : 0));
	});
	let famLabel = $derived((fid: string) => meta?.families.find((f) => f.id === fid)?.label ?? call?.families.find((f) => f.id === fid)?.label ?? fid);
	let readers = $derived(meta?.models.fact_readers ?? [
		{ id: 'qwen', label: 'Qwen', model: '' },
		{ id: 'kev', label: 'Kev', model: '' }
	]);
	const pc = (x: number | null | undefined) => (x === null || x === undefined ? '–' : `${Math.round(x * 100)} %`);
	// fact values of one category, by fact id
	const valuesOf = (fam: string | null | undefined): Record<string, FactValue> =>
		Object.fromEntries((fam && call?.facts[fam]) ? call.facts[fam].map((f) => [f.id, f.resolved]) : []);
	let actual = $derived(valuesOf(call?.decision.family));

	// Why the system decided this (one line under the verdict): which rule fired, and, when the label is not
	// the rule's own outcome, where the score sits against the thresholds; plus the rule's unclear facts.
	let verdictWhy = $derived.by(() => {
		if (!call) return { line: '', unclear: [] as FactAnswer[] };
		const d = call.decision;
		const r = d.rule;
		const fam = (d.family && call.facts[d.family]) || [];
		const ids = r?.condition_tree ? new Set(factsOf(r.condition_tree)) : null;
		const unclear = fam.filter((f) => f.resolved === 'unclear' && (!ids || ids.has(f.id)));
		const parts: string[] = [];
		const score = () =>
			d.label === 'alarm'
				? `score ${p2(d.score)} ≥ alarm threshold ${p2(d.threshold)}`
				: d.label === 'review'
					? `score ${p2(d.score)}, below alarm threshold ${p2(d.threshold)}`
					: `score ${p2(d.score)}, below review from ${p2(d.review_floor)}`;
		// fail closed (fusion/two_readers.py escalate_missing_reader): a missing reader makes it at least Review
		const missing = d.reasons.map((x) => x.match(/^Leser (.+?) ausgefallen/)).find(Boolean);
		if (missing) parts.push(`Fact reader ${missing[1]} failed: facts incomplete, so at least Review`);
		if (r) {
			parts.push(`${LABEL[r.outcome]} rule matched`);
			if (r.outcome !== d.label) parts.push(score());
		} else {
			parts.push('No rule matched');
			if (d.label !== 'no_alert' && !missing) parts.push(`flagged by keyword / pattern cues · ${score()}`);
		}
		if (unclear.length) {
			const dis = unclear.filter((f) => !f.agree).length;
			const what = dis === unclear.length ? 'readers disagree' : dis === 0 ? 'both readers unsure' : `readers disagree on ${dis}`;
			parts.push(`${unclear.length} ${unclear.length === 1 ? 'fact' : 'facts'} unclear (${what})`);
		} else if (r && ids?.size) {
			parts.push('readers agree on every fact of the rule');
		}
		return { line: parts.join(' · '), unclear };
	});

	// legal basis: the table marks unconfirmed ones with a German suffix; show it as a small tag
	const PROPOSED = /\s*[–-]\s*Vorschlag, durch Compliance zu bestätigen\.?\s*$/;

	// passage evidence, grouped by fact; keywords and patterns as chips
	function evidenceOf(p: { family: string; sources?: PassageSource[]; reasons: string[] }) {
		const facts = new Map<string, { label: string; value?: FactValue; lines: PassageSource[] }>();
		const chips: { text: string; kind: string }[] = [];
		const notes: string[] = [];
		const fam = call?.facts[p.family] ?? [];
		for (const s of p.sources ?? []) {
			if (s.source === 'keyword' || s.source === 'pattern') {
				const t = s.phrase || s.text;
				if (!chips.some((c) => c.text === t)) chips.push({ text: t, kind: s.source });
			} else if (s.source === 'note' || !s.fact) {
				notes.push(s.text);
			} else {
				const g = facts.get(s.fact) ?? {
					label: s.fact_label || s.fact,
					value: fam.find((f) => f.id === s.fact)?.resolved,
					lines: []
				};
				if (!g.lines.some((l) => l.source === s.source && l.why === s.why && l.p_without === s.p_without)) g.lines.push(s);
				facts.set(s.fact, g);
			}
		}
		if (!p.sources?.length) notes.push(...p.reasons);
		return { facts: [...facts.values()], chips, notes };
	}
	let speakerChange = (i: number) => i === 0 || segs[i - 1].role !== segs[i].role || segs[i - 1].speaker !== segs[i].speaker;
</script>

<svelte:window onkeydown={onKey} />
<svelte:head><title>{id} · Sherlock Phones</title></svelte:head>

{#if err}
	<p class="h2">Call not found.</p>
	<p><a href="/">Back to calls</a></p>
{:else if call}
	{@const d = call.decision}
	<!-- head -->
	<section class="grid head">
		<div class="ttl">
			<a class="small back" href="/">← All calls</a>
			<h1 class="h1 num">{call.id}</h1>
			<p class="small muted num facts-line">
				{time(call.duration)} · {call.passages.length} {call.passages.length === 1 ? 'passage' : 'passages'} · {call.keyword_hits.length} keyword {call.keyword_hits.length === 1 ? 'hit' : 'hits'}
				{#if call.reviews.length}· <b class="ok">reviewed</b>{/if}
			</p>
		</div>
		<div class="verdict">
			<p class="label muted">AI decision</p>
			<p class="display {d.label}">{LABEL[d.label]}</p>
			<p class="small vwhy" title="Score {p2(d.score)} · Review from {p2(d.review_floor)} · Alarm from {p2(d.threshold)}{verdictWhy.unclear.length ? '\nUnclear: ' + verdictWhy.unclear.map((f) => f.label).join('; ') : ''}">
				{verdictWhy.line}{#if d.stored_label !== d.label}<span class="muted"> · stored as {LABEL[d.stored_label]}</span>{/if}
			</p>
		</div>
	</section>

	<!-- why -->
	<section class="grid why">
		<p class="label side">Decision</p>
		<div class="why-main">
			{#if d.family_label}<p class="label fam-l" class:red={d.label === 'alarm'}>{d.family_label}</p>{/if}
			{#if d.rule}
				<p class="rtext" title="Rule {d.rule.id} → {LABEL[d.rule.outcome]}">{d.rule.title ? d.rule.title + '. ' : ''}{d.rule.text}</p>
				<div class="because"><Condition text={d.rule.condition_text} tree={d.rule.condition_tree} size="l" {actual} /></div>
			{:else}
				<p class="h2 because">{stripRule(d.reason)}</p>
			{/if}
		</div>
		{#if d.legal_basis}
			<div class="legal">
				<p class="label muted">Legal basis</p>
				<p class="small">{d.legal_basis.replace(PROPOSED, '')}{#if PROPOSED.test(d.legal_basis)} <span class="tag" title="Proposal, to be confirmed by compliance">proposed</span>{/if}</p>
			</div>
		{/if}
	</section>

	<div class="grid work">
		<!-- left: listen + read -->
		<section class="listen" aria-label="Recording and transcript">
			<div class="stick">
				<div class="player">
					<button class="play" onclick={() => clock.toggle()} aria-label={clock.playing ? 'Pause' : 'Play'}>
						{#if clock.playing}
							<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="4" y="3" width="4" height="14" /><rect x="12" y="3" width="4" height="14" /></svg>
						{:else}
							<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3 L17 10 L5 17 Z" /></svg>
						{/if}
					</button>
					<div class="tl-wrap">
						<div class="clock num"><b>{time(clock.t)}</b> <span class="muted">/ {time(clock.duration)}</span></div>
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<div
							class="bar"
							role="slider"
							tabindex="0"
							aria-label="Position"
							aria-valuemin={0}
							aria-valuemax={Math.round(clock.duration)}
							aria-valuenow={Math.round(clock.t)}
							aria-valuetext={time(clock.t)}
							onclick={onBar}
							onkeydown={onBarKey}
						>
							{#each call.passages as p}
								<span class="pz" style="left:{(p.start / clock.duration) * 100}%;width:{Math.max(0.6, ((p.end - p.start) / clock.duration) * 100)}%"></span>
							{/each}
							<span class="fill" style="width:{(clock.t / (clock.duration || 1)) * 100}%"></span>
							<span class="head-mark" style="left:{(clock.t / (clock.duration || 1)) * 100}%"></span>
						</div>
					</div>
					<div class="rate" role="group" aria-label="Speed">
						{#each [1, 1.25, 1.5] as r}
							<button class:on={clock.rate === r} onclick={() => clock.setRate(r)} aria-pressed={clock.rate === r}>{r}×</button>
						{/each}
					</div>
				</div>
				{#if src}
					<audio bind:this={audioEl} {src} preload="metadata" onended={() => clock.ended()} onerror={() => (clock.audio = false)}></audio>
				{/if}
				{#if !clock.audio}
					<p class="noaudio small muted">No audio here: playback runs the transcript only.</p>
				{/if}

				<div class="tools">
					<div class="seg" role="radiogroup" aria-label="Transcript language">
						<label><input type="radio" bind:group={view} value="de" /><span>Standard German</span></label>
						<label title={call.swiss_german ? '' : 'Not available for this call'}><input type="radio" bind:group={view} value="gsw" disabled={!call.swiss_german} /><span>Swiss German</span></label>
					</div>
					{#if !follow}
						<button class="btn small" onclick={() => (follow = true)}>Follow playback</button>
					{/if}
				</div>
			</div>

				{#if call.passages.length}
					<ol class="passages" aria-label="Suspicious passages">
						{#each call.passages as p, i}
							{@const ev = evidenceOf(p)}
							<li class:on={playingPassage === i}>
								<button class="pbtn" onclick={() => playPassage(i)} aria-label="{playingPassage === i ? 'Pause' : 'Play'} passage {i + 1}, {time(p.start)} to {time(p.end)}">
									<span class="pn">
										{#if playingPassage === i}
											<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="5" y="4" width="3.5" height="12" /><rect x="11.5" y="4" width="3.5" height="12" /></svg>
										{:else}
											<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4 L16 10 L6 16 Z" /></svg>
										{/if}
										P{i + 1}
									</span>
									<span class="num">{time(p.start)}–{time(p.end)}</span>
									<span class="pf">{p.family_label}</span>
								</button>
								{#if ev.facts.length || ev.chips.length || ev.notes.length}
									<div class="pev small">
										{#each ev.facts as g}
											<div class="pfact">
												<p class="pfl">{g.label}{#if g.value}<span class="pval {g.value}" title="Value in this call (both readers combined)">{g.value}</span>{/if}</p>
												{#each g.lines as l}
													<p class="pline">
														<b>{l.source_label}</b>
														{#if l.method === 'mask'}
															<span>yes {pc(l.p_yes)}; without this passage {pc(l.p_without)}</span>
														{:else if l.why}
															<span>{l.why}</span>
														{:else}
															<span>{l.value ?? ''} {pc(l.p_yes)}</span>
														{/if}
													</p>
												{/each}
											</div>
										{/each}
										{#if ev.chips.length}
											<p class="chips">
												{#each ev.chips as c}<span class="chip" title={c.kind === 'keyword' ? 'Keyword' : 'Number pattern'}>{c.text}</span>{/each}
											</p>
										{/if}
										{#each ev.notes as n}<p class="pline muted">{n}</p>{/each}
									</div>
								{/if}
							</li>
						{/each}
					</ol>
				{/if}

				<div class="tx" role="region" aria-label="Transcript" bind:this={box} onwheel={userScrolled} ontouchmove={userScrolled} tabindex="-1">
					{#if view === 'gsw'}
						<p class="label muted gswnote">Transcribed from the audio by our Swiss German dialect model, for reading only</p>
					{/if}
					<ol>
						{#each segs as s, i (s.id)}
							{@const pi = passageOf.get(s.id)}
							<li
								data-i={i}
								class:act={i === active}
								class:past={i < active}
								class:pass={pi !== undefined}
								class:ev={evidence.has(s.id)}
								class:newspk={speakerChange(i)}
							>
								<button class="seg-btn" onclick={() => seekTo(s.start)} aria-label="Play from {time(s.start)}">
									<span class="ts num">{time(s.start)}</span>
									<span class="who">{speakerChange(i) ? role(s.role) || s.speaker : ''}</span>
									<span class="text">
										{#each highlight(s.text, hitsBySeg.get(s.id)) as part}{#if part.hit}<mark>{part.t}</mark>{:else}{part.t}{/if}{/each}
									</span>
									{#if pi !== undefined && passageStart.has(s.id)}
										<span class="ptag">P{pi + 1}</span>
									{/if}
								</button>
								{#if i === active}
									<span class="prog" style="width:{Math.min(100, ((clock.t - s.start) / Math.max(0.1, s.end - s.start)) * 100)}%"></span>
								{/if}
							</li>
						{/each}
					</ol>
				</div>
				<p class="keys small muted">Space play/pause · ← → 5 s · N next passage · P previous · click a line to play from there</p>
		</section>

		<!-- right: facts + review -->
		<section class="judge" aria-label="Facts and review">
			<h2 class="h2 sub">Facts</h2>
			{#each familyOrder as fid}
				<FactsTable
					family={fid}
					label={famLabel(fid)}
					decided={fid === decided}
					startOpen={!call.decision.rule && call.facts[fid].some((f) => f.resolved === 'yes')}
					facts={call.facts[fid]}
					{readers}
					bind:corrections
					onEvidence={showEvidence}
				/>
			{/each}

			<ReviewForm {call} {corrections} families={meta?.families ?? []} />
		</section>
	</div>
{:else}
	<p class="muted">Loading…</p>
{/if}

<style>
	.head {
		align-items: end;
		padding-bottom: 32px;
	}
	.ttl {
		grid-column: 1 / span 7;
	}
	.back {
		display: inline-block;
		margin-bottom: 16px;
	}
	.facts-line {
		margin-top: 12px;
	}
	.ok {
		color: var(--black);
	}
	.verdict {
		grid-column: 8 / span 5;
	}
	.verdict .display {
		margin: 4px 0 8px;
	}
	.display.alarm {
		color: var(--red);
	}
	.display.no_alert {
		color: var(--grey-3);
	}

	.why {
		border-top: var(--rule-thick);
		padding: 16px 0 40px;
	}
	.side {
		grid-column: 1 / span 2;
	}
	.why-main {
		grid-column: 3 / span 6;
	}
	.because {
		margin: 8px 0 16px;
	}
	p.because {
		max-width: 30ch;
	}
	.rtext {
		max-width: 60ch;
		margin: 6px 0 4px;
		font-size: var(--t-m);
	}
	.legal {
		grid-column: 10 / span 3;
	}
	.legal p + p {
		margin-top: 4px;
	}

	.work {
		border-top: var(--rule);
		padding-top: 24px;
		align-items: start;
	}
	.listen {
		grid-column: 1 / span 7;
	}
	.stick {
		position: sticky;
		top: var(--head-h, 104px);
		background: var(--white);
		z-index: 2;
		padding: 8px 0 4px;
	}
	.judge {
		grid-column: 9 / span 4;
	}
	.sub {
		margin: 4px 0 24px;
	}

	/* player */
	.player {
		display: grid;
		grid-template-columns: 56px 1fr auto;
		gap: 16px;
		align-items: center;
	}
	.play {
		width: 56px;
		height: 56px;
		background: var(--black);
		border: 0;
		cursor: pointer;
		display: grid;
		place-items: center;
	}
	.play:hover {
		background: var(--red);
	}
	.play svg {
		width: 20px;
		height: 20px;
		fill: var(--white);
	}
	.clock {
		font-size: var(--t-s);
		margin-bottom: 6px;
	}
	.bar {
		position: relative;
		height: 24px;
		cursor: pointer;
		background: linear-gradient(var(--black), var(--black)) 0 50% / 100% 1px no-repeat;
	}
	.bar .fill {
		position: absolute;
		left: 0;
		top: 50%;
		height: 3px;
		margin-top: -1px;
		background: var(--black);
	}
	.bar .pz {
		position: absolute;
		top: 4px;
		bottom: 4px;
		background: var(--red);
		opacity: 0.9;
	}
	.bar .head-mark {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 2px;
		margin-left: -1px;
		background: var(--black);
	}
	.rate {
		display: flex;
		gap: 2px;
	}
	.rate button {
		border: 0;
		background: none;
		font-size: var(--t-xs);
		font-weight: 600;
		padding: 6px;
		cursor: pointer;
		color: var(--grey-ink);
	}
	.rate button.on {
		color: var(--black);
		text-decoration: underline;
		text-underline-offset: 3px;
	}
	.noaudio {
		margin-top: 8px;
	}

	.tools {
		margin-top: 20px;
		display: flex;
		gap: 16px;
		align-items: center;
		flex-wrap: wrap;
	}
	.seg input:disabled + span {
		opacity: 0.35;
	}

	.passages {
		margin-top: 16px;
		border-top: var(--rule);
	}
	.passages > li {
		border-bottom: var(--hair);
		padding: 10px 0;
	}
	.pbtn {
		display: grid;
		grid-template-columns: auto auto 1fr;
		column-gap: 12px;
		align-items: center;
		text-align: left;
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
		font-size: var(--t-s);
		width: 100%;
	}
	.pbtn:hover .pn,
	li.on .pn {
		background: var(--black);
	}
	.pn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		background: var(--red);
		color: var(--white);
		font-weight: 700;
		padding: 3px 8px 3px 6px;
	}
	.pn svg {
		width: 12px;
		height: 12px;
		fill: currentColor;
	}
	.pf {
		font-weight: 600;
	}
	.pev {
		margin: 6px 0 0 0;
		padding-left: 64px;
	}
	.pfact + .pfact {
		margin-top: 6px;
	}
	.pfl {
		font-weight: 600;
	}
	.pval {
		margin-left: 8px;
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--grey-ink);
	}
	.pval.yes {
		color: var(--black);
	}
	.pval.unclear {
		color: var(--red-ink);
	}
	.pline {
		color: var(--grey-ink);
		overflow-wrap: anywhere;
	}
	.pline b {
		color: var(--black);
		font-weight: 600;
		margin-right: 6px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 6px;
	}
	.chip {
		border: 1px solid var(--black);
		padding: 1px 8px;
		font-size: var(--t-xs);
		font-weight: 600;
	}
	.tag {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		border: 1px solid var(--grey-3);
		color: var(--grey-ink);
		padding: 0 6px;
		white-space: nowrap;
		margin-left: 6px;
	}
	.vwhy {
		max-width: 46ch;
	}
	.fam-l {
		color: var(--grey-ink);
	}
	.fam-l.red {
		color: var(--red-ink);
	}

	/* transcript */
	.tx {
		margin-top: 16px;
		height: calc(100vh - 400px);
		min-height: 320px;
		overflow-y: auto;
		border-top: var(--rule);
		position: relative;
		scrollbar-width: thin;
	}
	.tx:focus {
		outline: none;
	}
	.gswnote {
		padding: 12px 0;
		border-bottom: var(--hair);
	}
	.tx li {
		position: relative;
	}
	.tx li.newspk {
		margin-top: 12px;
	}
	.seg-btn {
		display: grid;
		grid-template-columns: 48px 80px 1fr 32px;
		column-gap: 12px;
		width: 100%;
		text-align: left;
		background: none;
		border: 0;
		padding: 6px 0;
		cursor: pointer;
		color: var(--grey-ink);
		line-height: 1.5;
		font-size: var(--t-m);
	}
	.seg-btn:hover .text {
		text-decoration: underline;
		text-decoration-color: var(--grey-3);
		text-underline-offset: 4px;
	}
	.past .seg-btn {
		color: var(--black);
	}
	.act .seg-btn {
		color: var(--black);
		font-weight: 600;
	}
	.ts {
		font-size: var(--t-xs);
		padding-top: 4px;
		color: var(--grey-ink);
	}
	.act .ts {
		color: var(--red-ink);
		font-weight: 700;
	}
	.who {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		padding-top: 4px;
		color: var(--black);
	}
	.pass .seg-btn {
		box-shadow: inset 3px 0 0 var(--red);
		padding-left: 0;
	}
	.pass .ts {
		padding-left: 8px;
	}
	.ev .seg-btn {
		background: var(--grey-1);
	}
	.ptag {
		font-size: var(--t-xs);
		font-weight: 700;
		color: var(--red-ink);
		padding-top: 4px;
		text-align: right;
	}
	.prog {
		position: absolute;
		left: 140px;
		bottom: 0;
		height: 2px;
		background: var(--red);
		max-width: calc(100% - 140px - 44px);
	}
	mark {
		background: none;
		color: inherit;
		text-decoration: underline;
		text-decoration-color: var(--red);
		text-decoration-thickness: 3px;
		text-underline-offset: 3px;
	}
	.keys {
		margin-top: 8px;
		font-size: var(--t-xs);
	}

	@media (max-width: 1100px) {
		.ttl,
		.verdict,
		.why-main,
		.legal,
		.listen,
		.judge {
			grid-column: 1 / span 12;
		}
		.side {
			grid-column: 1 / span 12;
		}
		.judge {
			margin-top: 48px;
		}
		.stick {
			position: static;
		}
	}
</style>
