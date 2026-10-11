<script lang="ts" module>
	import type { CondNode, FactValue } from '#lib/types.ts';

	const VALS: FactValue[] = ['yes', 'unclear', 'no'];

	/** Parse the API's condition_text ("A" is yes AND ("B" is not no OR "C" is yes)) into a tree. Used only
	 * when the API sent no condition_tree (older sample data). AND binds tighter than OR, as in the rule engine. */
	export function parseConditionText(text: string): CondNode {
		const toks = text.match(/"[^"]*"|\(|\)|[^\s()"]+/g) ?? [];
		let i = 0;
		const peek = () => toks[i];
		function atom(): CondNode {
			const t = toks[i++];
			if (t === '(') {
				const n = orExpr();
				if (peek() === ')') i++;
				return n;
			}
			if (t === 'NOT') {
				return { op: 'not', item: atom() };
			}
			if (t === 'always') return { op: 'true' };
			if (t?.startsWith('"')) {
				const label = t.slice(1, -1);
				if (peek() === 'is') i++;
				let neg = false;
				if (peek() === 'not') {
					neg = true;
					i++;
				}
				const v = toks[i++] as string;
				const values: FactValue[] =
					v === 'anything' ? [...VALS] : neg ? VALS.filter((x) => x !== v) : VALS.filter((x) => x === v);
				return { op: 'fact', fact: '', label, values };
			}
			return { op: 'fact', fact: '', label: t ?? '', values: [] };
		}
		function andExpr(): CondNode {
			const items = [atom()];
			while (peek() === 'AND') {
				i++;
				items.push(atom());
			}
			return items.length === 1 ? items[0] : { op: 'and', items };
		}
		function orExpr(): CondNode {
			const items = [andExpr()];
			while (peek() === 'OR') {
				i++;
				items.push(andExpr());
			}
			return items.length === 1 ? items[0] : { op: 'or', items };
		}
		try {
			return orExpr();
		} catch {
			return { op: 'fact', fact: '', label: text, values: [] };
		}
	}

	/** What a fact test needs, in words. */
	export function need(values: FactValue[]): string {
		const v = VALS.filter((x) => values.includes(x));
		if (v.length === 3) return 'anything';
		if (v.length === 1) return v[0];
		if (v.length === 2) {
			const missing = VALS.find((x) => !v.includes(x));
			return missing === 'no' ? 'yes or unclear' : 'not ' + missing;
		}
		return '';
	}

	/** Does the node hold for these fact values? undefined when a value is unknown. */
	export function holds(n: CondNode, actual: Record<string, FactValue>): boolean | undefined {
		if (n.op === 'true') return true;
		if (n.op === 'fact') {
			const a = n.fact ? actual[n.fact] : undefined;
			return a === undefined ? undefined : n.values.includes(a);
		}
		if (n.op === 'not') {
			const h = holds(n.item, actual);
			return h === undefined ? undefined : !h;
		}
		const hs = n.items.map((x) => holds(x, actual));
		if (hs.some((h) => h === undefined)) return undefined;
		return n.op === 'and' ? hs.every(Boolean) : hs.some(Boolean);
	}

	/** Fact ids a condition reads. */
	export function factsOf(n: CondNode | null | undefined): string[] {
		if (!n) return [];
		if (n.op === 'fact') return n.fact ? [n.fact] : [];
		if (n.op === 'not') return factsOf(n.item);
		if (n.op === 'true') return [];
		return n.items.flatMap(factsOf);
	}
</script>

<script lang="ts">
	// A rule condition as stacked clauses. An OR group inside an AND shows as one "one of" block, so the
	// grouping of the rule is visible. With `actual` (the call's fact values) each clause shows the call's value,
	// and clauses that do not hold are dimmed.
	interface Props {
		text: string;
		tree?: CondNode | null;
		size?: 'l' | 's';
		actual?: Record<string, FactValue> | null;
	}
	let { text, tree = null, size = 's', actual = null }: Props = $props();

	let root = $derived<CondNode>(tree ?? parseConditionText(text));
	// the top level as a list of rows joined by one connector
	let top = $derived.by(() => {
		const r = root;
		if (r.op === 'and' || r.op === 'or') return { join: r.op, items: r.items };
		return { join: 'and' as const, items: [r] };
	});
	const off = (n: CondNode) => (actual ? holds(n, actual) === false : false);
</script>

{#snippet clause(n: CondNode)}
	{#if n.op === 'fact'}
		<span class="f">{n.label}</span>
		<span class="v {n.values.length === 1 ? n.values[0] : ''}">{need(n.values)}</span>
		{#if actual}
			{@const a = n.fact ? actual[n.fact] : undefined}
			<span class="a {a ?? ''}" title="Value in this call">{a ?? '–'}</span>
		{/if}
	{:else if n.op === 'true'}
		<span class="f">Always</span><span></span>{#if actual}<span></span>{/if}
	{:else}
		{@const inner = n.op === 'not' ? n.item : n}
		{@const items = inner.op === 'and' || inner.op === 'or' ? inner.items : [inner]}
		<div class="grp">
			<span class="gl"
				>{n.op === 'not' ? (inner.op === 'or' ? 'None of' : 'Not all of') : inner.op === 'or' ? 'One of' : 'All of'}</span
			>
			<ol>
				{#each items as c, k}
					<li class:off={off(c)}>
						<span class="j">{k === 0 ? '' : inner.op === 'or' ? 'or' : 'and'}</span>
						{@render clause(c)}
					</li>
				{/each}
			</ol>
		</div>
	{/if}
{/snippet}

<ol class="cond {size}" class:withA={!!actual}>
	{#if actual}
		<li class="hd" aria-hidden="true"><span></span><span></span><span class="j">Needs</span><span class="j r">This call</span></li>
	{/if}
	{#each top.items as n, k}
		<li class:off={off(n)} class:group={n.op !== 'fact' && n.op !== 'true'}>
			<span class="j">{k === 0 ? '' : top.join}</span>
			{@render clause(n)}
		</li>
	{/each}
</ol>

<style>
	.cond li {
		display: grid;
		grid-template-columns: 36px 1fr auto;
		gap: 12px;
		align-items: baseline;
		padding: 4px 0;
	}
	.cond.withA li {
		grid-template-columns: 36px 1fr auto 64px;
	}
	.cond li.group {
		grid-template-columns: 36px 1fr;
	}
	.cond.l > li {
		grid-template-columns: 48px 1fr auto;
		padding: 6px 0;
		border-bottom: var(--hair);
	}
	.cond.l.withA > li {
		grid-template-columns: 48px 1fr auto 72px;
	}
	.cond.l > li.group {
		grid-template-columns: 48px 1fr;
	}
	.cond.l .f {
		font-size: var(--t-m);
		font-weight: 600;
		letter-spacing: -0.01em;
		line-height: 1.25;
	}
	.grp {
		border-left: 2px solid var(--black);
		padding-left: 12px;
	}
	.grp ol li {
		grid-template-columns: 28px 1fr auto;
		padding: 3px 0;
	}
	.cond.withA .grp ol li {
		grid-template-columns: 28px 1fr auto 64px;
	}
	.cond.l > li.hd {
		padding: 0 0 2px;
	}
	.r {
		text-align: right;
	}
	.gl,
	.j {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--grey-ink);
	}
	.gl {
		display: block;
		margin-bottom: 2px;
	}
	.v,
	.a {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		white-space: nowrap;
	}
	.v.no {
		color: var(--grey-ink);
	}
	.a {
		text-align: right;
		color: var(--grey-ink);
	}
	.a.yes {
		color: var(--black);
	}
	.a.unclear {
		color: var(--red-ink);
	}
	li.off > .f,
	li.off > .v,
	li.off > .a,
	li.off > .grp {
		opacity: 0.4;
	}
</style>
