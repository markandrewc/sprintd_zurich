<script lang="ts">
	import { tick } from 'svelte';
	import { get, post, patch, del, conn, bump, setRulebook } from '#lib/api.svelte.ts';
	import { LABEL, O, SQ, ruleName } from '#lib/format.ts';
	import PageHead from '#lib/components/PageHead.svelte';
	import Condition from '#lib/components/Condition.svelte';
	import type { Effect, Label, Meta, Rule, RuleDraft, RuleDraftFact, RulePreview, RulesResponse } from '#lib/types.ts';

	let rules = $state<RulesResponse | null>(null);
	let meta = $state<Meta | null>(null);
	let msg = $state<{ text: string; effect?: Effect; error?: boolean } | null>(null);

	let loadErr = $state('');
	function load() {
		get<RulesResponse>('/api/rules')
			.then((r) => {
				rules = r;
				loadErr = '';
			})
			.catch((e) => {
				rules = null;
				loadErr = e.status === 400 ? 'Rules cannot be edited for this profile.' : e.message;
			});
	}
	$effect(() => {
		conn.epoch;
		load();
		get<Meta>('/api/meta').then((m) => (meta = m)).catch(() => {});
	});

	let total = $derived(meta?.counts.calls ?? 0);
	let demo = $derived((rules?.rulebook ?? conn.rulebook)?.mode === 'demo');
	let ruleCount = $derived(rules ? rules.families.reduce((n, f) => n + f.rules.length, 0) + rules.cross_rules.length : 0);

	// ---------- demo rule book (in API memory; the rule book file is never touched) ----------
	let switching = $state(false);
	async function switchBook(mode: 'demo' | 'production') {
		switching = true;
		try {
			const r = await setRulebook(mode);
			const n = r.effect.changed.length;
			msg = { text: `${n} ${n === 1 ? 'call' : 'calls'} changed`, effect: r.effect };
			if (mode === 'demo') openBuilder();
		} catch (e: any) {
			msg = { text: e.message, error: true };
		} finally {
			switching = false;
		}
	}
	let author = $derived(conn.user || 'officer');

	// ---------- builder (opened with «New rule») ----------
	let builderOpen = $state(false);
	let builderEl = $state<HTMLElement | null>(null);
	const blank = (): RuleDraftFact => ({ family: '', fact: '', value: 'yes', negate: false });
	let facts = $state<RuleDraftFact[]>([blank()]);
	let join = $state<'and' | 'or'>('and');
	let outcome = $state<Label>('review');
	let title = $state('');
	let description = $state('');
	let reportAs = $state('');
	let preview = $state<RulePreview | null>(null);
	let previewErr = $state('');
	let saving = $state(false);

	let complete = $derived(facts.filter((f) => f.family && f.fact));
	let fams = $derived([...new Set(complete.map((f) => f.family))]);
	let cross = $derived(fams.length > 1);

	function draft(): RuleDraft {
		return {
			facts: complete,
			join,
			outcome,
			title: title.trim(),
			description: description.trim(),
			report_as: cross ? reportAs || fams[0] : null,
			author
		};
	}

	let pt: ReturnType<typeof setTimeout>;
	let seq = 0;
	let pending = $state(false);
	// only the logic matters for the count; title / description do not trigger a new preview
	let logicKey = $derived(JSON.stringify({ f: complete, join, outcome, r: cross ? reportAs || fams[0] : null }));
	$effect(() => {
		logicKey;
		clearTimeout(pt);
		if (!complete.length) {
			preview = null;
			pending = false;
			return;
		}
		pending = true;
		const mine = ++seq;
		pt = setTimeout(async () => {
			try {
				const r = await post<RulePreview>('/api/rules/preview', $state.snapshot(draft()));
				if (mine !== seq) return;
				preview = r;
				previewErr = '';
			} catch (e: any) {
				if (mine !== seq) return;
				previewErr = e.message;
				preview = null;
			} finally {
				if (mine === seq) pending = false;
			}
		}, 250);
	});

	// empty demo book: open the builder at once (instead of a box that tells you to)
	let autoOpened = false;
	$effect(() => {
		if (demo && rules && ruleCount === 0 && !builderOpen && !autoOpened) {
			autoOpened = true;
			openBuilder();
		}
	});

	async function openBuilder() {
		builderOpen = true;
		await tick();
		builderEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		builderEl?.querySelector<HTMLSelectElement>('select')?.focus({ preventScroll: true });
	}

	function closeBuilder() {
		builderOpen = false;
		facts = [blank()];
		join = 'and';
		outcome = 'review';
		title = '';
		description = '';
		reportAs = '';
		preview = null;
	}

	function factKey(f: RuleDraftFact) {
		return f.family && f.fact ? `${f.family}.${f.fact}` : '';
	}
	function setFact(i: number, key: string) {
		const [family, fact] = key.split('.');
		facts[i] = { ...facts[i], family: family ?? '', fact: fact ?? '' };
	}

	async function save() {
		if (!complete.length || !title.trim()) return;
		saving = true;
		try {
			const r = await post<RulePreview>('/api/rules', draft());
			msg = { text: demo ? `Rule “${title.trim()}” added to the demo rule book.` : `Rule “${title.trim()}” is live.`, effect: r.effect };
			autoOpened = true;
			closeBuilder();
			bump();
		} catch (e: any) {
			msg = { text: e.message, error: true };
		} finally {
			saving = false;
		}
	}

	// ---------- list actions ----------
	// one change at a time: a rule-book write + re-decision of every call takes a moment (more with many calls)
	let busy = $state(false);
	async function act(fn: () => Promise<{ effect?: Effect }>, text: string) {
		if (busy) return;
		busy = true;
		msg = { text: 'Applying…' };
		try {
			const r = await fn();
			msg = { text, effect: r.effect };
			bump();
		} catch (e: any) {
			msg = { text: e.message, error: true };
		} finally {
			busy = false;
		}
	}
	const toggle = (r: Rule) =>
		act(() => patch(`/api/rules/${encodeURIComponent(r.id)}`, { enabled: !r.enabled, author }), `${r.enabled ? 'Switched off' : 'Switched on'}: “${ruleName(r)}”`);
	const move = (r: Rule, d: number) =>
		act(() => patch(`/api/rules/${encodeURIComponent(r.id)}`, { move: d, author }), `Moved ${d < 0 ? 'up' : 'down'}: “${ruleName(r)}”`);
	const remove = (r: Rule) => {
		if (!confirm(`Delete rule “${ruleName(r)}”?`)) return;
		act(() => del(`/api/rules/${encodeURIComponent(r.id)}?author=${encodeURIComponent(author)}`), `Deleted: “${ruleName(r)}”`);
	};
	const undo = () => act(() => post('/api/rules/undo', { author }), 'Last change undone.');

	const famLabel = (id: string) => rules?.families.find((f) => f.id === id)?.label ?? id;
</script>

<svelte:head><title>Rules · Sherlock Phones</title></svelte:head>

<PageHead n="02 Settings" title="Rules" lead="Rules turn facts into Alarm, Review or No alert.">
	{#if !demo && rules?.version != null}
		<p class="small muted num">Version {rules.version}</p>
	{/if}
	<div class="hb">
		<button class="btn" onclick={undo} disabled={!rules?.can_undo || busy}>Undo last change</button>
		<button class="btn primary" onclick={openBuilder} disabled={builderOpen || !rules}>+ New rule</button>
	</div>
	{#if rules && !demo}
		<div class="hb">
			<button class="btn link small" onclick={() => switchBook('demo')} disabled={switching} title="Start an empty rule book in the API's memory. The rule book file is not changed.">Empty rule book (demo)</button>
		</div>
	{/if}
	<p class="small adv"><a href="/settings/advanced">Advanced →</a></p>
</PageHead>

{#if loadErr}
	<div class="msg err" role="status">
		<p><b>{loadErr}</b></p>
	</div>
{/if}

{#if msg}
	<div class="msg" class:err={msg.error} role="status">
		<p><b>{msg.text}</b>{#if msg.effect} <span class="muted">{msg.effect.summary}</span>{/if}</p>
		{#if !msg.error && !busy && rules?.can_undo}<button class="btn link small" onclick={undo}>Undo</button>{/if}
		<button class="btn link small" onclick={() => (msg = null)} aria-label="Dismiss">Close</button>
	</div>
{/if}

<!-- builder -->
{#if builderOpen}
	<section class="builder" aria-labelledby="b-h" bind:this={builderEl}>
		<div class="grid">
			<h2 id="b-h" class="h2 bt">New rule</h2>
			<button class="btn link small cancel" onclick={closeBuilder}>Cancel</button>
		</div>
		<div class="grid steps">
			<fieldset class="step s1">
				<legend><span class="sn">1</span>Facts</legend>
				<ol>
					{#each facts as f, i}
						<li class="fr">
							<span class="jn">{i === 0 ? 'if' : join}</span>
							<select class="field" value={factKey(f)} onchange={(e) => setFact(i, e.currentTarget.value)} aria-label="Fact {i + 1}">
								<option value="">Choose a fact…</option>
								{#each rules?.families ?? [] as fam}
									<optgroup label={fam.label}>
										{#each fam.facts as ff}<option value="{fam.id}.{ff.id}">{ff.label}</option>{/each}
									</optgroup>
								{/each}
							</select>
							<span class="isrow">
								<span class="seg sm">
									<label><input type="radio" name="neg{i}" checked={!f.negate} onchange={() => (facts[i].negate = false)} /><span>is</span></label>
									<label><input type="radio" name="neg{i}" checked={f.negate} onchange={() => (facts[i].negate = true)} /><span>is not</span></label>
								</span>
								<span class="seg sm">
									{#each ['yes', 'no', 'unclear'] as v}
										<label><input type="radio" name="val{i}" value={v} bind:group={facts[i].value} /><span>{v}</span></label>
									{/each}
								</span>
								{#if facts.length > 1}
									<button class="btn link small" onclick={() => facts.splice(i, 1)} aria-label="Remove fact {i + 1}">Remove</button>
								{/if}
							</span>
						</li>
					{/each}
				</ol>
				<button class="btn small add" onclick={() => facts.push(blank())}>+ Add fact</button>
			</fieldset>

			<fieldset class="step s2">
				<legend><span class="sn">2</span>Combine</legend>
				<div class="stack">
					<label class="opt"><input type="radio" bind:group={join} value="and" /><span><b>All</b> must hold</span></label>
					<label class="opt"><input type="radio" bind:group={join} value="or" /><span><b>Any</b> is enough</span></label>
				</div>
				<legend class="sub"><span class="sn">3</span>Outcome</legend>
				<div class="stack">
					{#each ['alarm', 'review', 'no_alert'] as o}
						<label class="opt"><input type="radio" bind:group={outcome} value={o} /><span><span class="sq {SQ[o as Label]}"></span>{LABEL[o as Label]}</span></label>
					{/each}
				</div>
				{#if cross}
					<label class="sub blk">
						<span class="label">Report under</span>
						<select class="field" bind:value={reportAs}>
							{#each fams as f}<option value={f}>{famLabel(f)}</option>{/each}
						</select>
					</label>
				{/if}
			</fieldset>

			<fieldset class="step s4">
				<legend><span class="sn">4</span>Name</legend>
				<label class="blk"><span class="label">Title</span><input class="field" bind:value={title} placeholder="e.g. Code given to a third party" /></label>
				<label class="blk sub"><span class="label">Description</span><textarea class="field" rows="2" bind:value={description}></textarea></label>
				<button class="btn primary save" onclick={save} disabled={!complete.length || !title.trim() || saving}>
					{saving ? 'Saving…' : 'Apply rule'}
				</button>
				{#if !conn.user}<p class="small muted">Saved as “officer”</p>{/if}
			</fieldset>

			<div class="live" aria-live="polite">
				<p class="label">Live{#if pending} <span class="muted">· counting…</span>{/if}</p>
				{#if preview}
					<p class="display num">{preview.hits.length}<span class="of">/{total}</span></p>
					<p class="small">calls match</p>
					<p class="small muted eff">{preview.effect.summary}</p>
					{#if preview.effect.changed.length}
						<ul class="small num chg">
							{#each preview.effect.changed.slice(0, 6) as c}
								<li><a href="/calls/{encodeURIComponent(c.id)}">{c.id}</a> <span class={O[c.before]}>{LABEL[c.before]}</span> → <span class={O[c.after]}>{LABEL[c.after]}</span></li>
							{/each}
						</ul>
					{/if}
				{:else if previewErr}
					<p class="small red">{previewErr}</p>
				{:else}
					<p class="display num muted">–</p>
					<p class="small muted">Pick a fact to see how many calls it matches.</p>
				{/if}
			</div>
		</div>
	</section>
{/if}

<!-- list -->
{#each rules?.families ?? [] as fam, fi}
	<section class="grid fam" aria-labelledby="f-{fam.id}">
		<div class="fh">
			<p class="label muted num">{String(fi + 1).padStart(2, '0')}</p>
			<h2 id="f-{fam.id}" class="h2">{fam.label}</h2>
			{#if fam.legal_basis}<p class="small muted lb">{fam.legal_basis}</p>{/if}
		</div>
		<ol class="rl">
			{#each fam.rules as r, i (r.id)}
				{@render ruleRow(r, i, fam.rules.length)}
			{:else}
				<li class="muted small">No rules.</li>
			{/each}
		</ol>
	</section>
{/each}

{#if rules?.cross_rules.length}
	<section class="grid fam" aria-labelledby="f-cross">
		<div class="fh">
			<p class="label muted">+</p>
			<h2 id="f-cross" class="h2">Across categories</h2>
		</div>
		<ol class="rl">
			{#each rules.cross_rules as r, i (r.id)}
				{@render ruleRow(r, i, rules.cross_rules.length)}
			{/each}
		</ol>
	</section>
{/if}

{#snippet ruleRow(r: Rule, i: number, n: number)}
	<li class="rule" class:off={!r.enabled}>
		<span class="pos num">{i + 1}</span>
		<div class="rbody">
			<p class="rh">
				<span class="sq {SQ[r.outcome]}" aria-hidden="true"></span><span class={O[r.outcome]}>{LABEL[r.outcome]}</span>
				<b class="rt" title="Rule {r.id}">{ruleName(r)}</b>
				{#if !r.enabled}<span class="label muted">off</span>{/if}
			</p>
			<Condition text={r.condition_text} tree={r.condition_tree} />
			{#if r.title && r.text}<p class="small muted rx">{r.text}</p>{/if}
		</div>
		<p class="hits num" title={r.hit_calls?.join(', ')}><span class="h2">{r.hits ?? 0}</span><span class="small muted cl">calls</span></p>
		<div class="ra">
			<button class="btn link small" onclick={() => toggle(r)} disabled={busy}>{r.enabled ? 'Switch off' : 'Switch on'}</button>
			<button class="btn link small" onclick={() => move(r, -1)} disabled={busy || i === 0} aria-label="Move “{ruleName(r)}” up">↑</button>
			<button class="btn link small" onclick={() => move(r, 1)} disabled={busy || i === n - 1} aria-label="Move “{ruleName(r)}” down">↓</button>
			<button class="btn link small" onclick={() => remove(r)} disabled={busy}>Delete</button>
		</div>
	</li>
{/snippet}

<style>
	.adv {
		margin-top: 12px;
	}
	.hb {
		display: flex;
		gap: 12px;
		justify-content: flex-end;
		margin-top: 8px;
	}
	.msg {
		display: flex;
		gap: 16px;
		align-items: baseline;
		padding: 12px 0;
		border-bottom: var(--rule);
	}
	.msg p {
		flex: 1;
	}
	.msg.err b {
		color: var(--red-ink);
	}

	.builder {
		margin-top: 48px;
		padding-bottom: 48px;
		border-bottom: var(--rule-thick);
		scroll-margin-top: calc(var(--head-h, 120px) + 16px); /* below the sticky header */
	}
	.bt {
		grid-column: 1 / span 10;
		margin-bottom: 24px;
	}
	.cancel {
		grid-column: 11 / span 2;
		justify-self: end;
		align-self: start;
	}
	.steps {
		align-items: start;
	}
	.step {
		border: 0;
		margin: 0;
		padding: 0;
		border-top: var(--rule);
		padding-top: 12px;
	}
	.s1 {
		grid-column: 1 / span 5;
	}
	.s2 {
		grid-column: 6 / span 2;
	}
	.s4 {
		grid-column: 8 / span 2;
	}
	.live {
		grid-column: 10 / span 3;
		border-top: 4px solid var(--red);
		padding-top: 12px;
	}
	legend {
		float: left;
		width: 100%;
		font-weight: 700;
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 0;
		margin-bottom: 12px;
	}
	legend.sub {
		margin-top: 28px;
	}
	.step > :not(legend) {
		clear: both;
	}
	.sn {
		font-size: var(--t-xs);
		width: 22px;
		height: 22px;
		display: inline-grid;
		place-items: center;
		background: var(--black);
		color: var(--white);
	}
	.fr {
		display: grid;
		grid-template-columns: 36px 1fr;
		column-gap: 12px;
		row-gap: 8px;
		padding: 8px 0 14px;
		border-bottom: var(--hair);
	}
	.jn {
		font-size: var(--t-xs);
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--grey-ink);
		padding-top: 12px;
	}
	.isrow {
		grid-column: 2;
		display: flex;
		gap: 12px;
		align-items: center;
		flex-wrap: wrap;
	}
	.seg.sm span {
		padding: 4px 10px;
		font-size: var(--t-xs);
	}
	.add {
		margin-top: 12px;
	}
	.stack {
		display: grid;
		gap: 0;
	}
	.opt {
		position: relative;
		display: block;
		cursor: pointer;
		border-bottom: var(--hair);
	}
	.opt input {
		position: absolute;
		opacity: 0;
	}
	.opt > span {
		display: block;
		padding: 8px 8px;
		font-size: var(--t-s);
	}
	.opt input:checked + span {
		background: var(--black);
		color: var(--white);
	}
	.opt input:checked + span .sq.none {
		border-color: var(--white);
	}
	.opt input:checked + span .sq.review {
		background: var(--white);
	}
	.opt input:focus-visible + span {
		outline: 3px solid var(--red);
		outline-offset: -3px;
	}
	.blk {
		display: block;
	}
	.sub.blk {
		margin-top: 16px;
	}
	.save {
		margin-top: 20px;
		width: 100%;
		justify-content: center;
	}
	.of {
		font-size: var(--t-xl);
		color: var(--grey-ink);
		letter-spacing: -0.02em;
	}
	.eff {
		margin-top: 12px;
	}
	.chg {
		margin-top: 8px;
	}
	.chg li {
		padding: 3px 0;
		border-bottom: var(--hair);
	}

	.fam {
		margin-top: 56px;
		align-items: start;
	}
	.fh {
		grid-column: 1 / span 3;
		position: sticky;
		top: 120px;
	}
	.fh .h2 {
		margin-top: 4px;
	}
	.lb {
		margin-top: 8px;
	}
	.rl {
		grid-column: 4 / span 9;
		border-top: var(--rule);
	}
	.rule {
		display: grid;
		grid-template-columns: 32px 1fr 96px 220px;
		gap: 16px;
		padding: 16px 0;
		border-bottom: var(--hair);
		align-items: start;
	}
	.rule.off .rbody {
		opacity: 0.45;
	}
	.pos {
		font-size: var(--t-l);
		font-weight: 700;
	}
	.rh {
		display: flex;
		gap: 12px;
		align-items: baseline;
		margin-bottom: 4px;
		flex-wrap: wrap;
	}
	.rx {
		margin-top: 4px;
	}
	.hits {
		text-align: right;
	}
	.cl {
		margin-left: 4px;
	}
	.ra {
		display: flex;
		gap: 14px;
		justify-content: flex-end;
		padding-top: 4px;
	}

	@media (max-width: 1100px) {
		.s1,
		.s2,
		.s4,
		.live,
		.fh,
		.rl {
			grid-column: 1 / span 12;
			margin-top: 24px;
			position: static;
		}
		.rule {
			grid-template-columns: 32px 1fr;
		}
	}
</style>
