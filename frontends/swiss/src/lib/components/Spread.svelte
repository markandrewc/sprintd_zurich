<script lang="ts">
	// Butterfly histogram of the readers' p(yes): first reader up, second reader down, one shared axis.
	// Bars take the zone of their bin centre at the current cutoff c: yes (black), unclear (red), no (grey).
	// Purely visual; the decisions themselves come from the API.
	interface Props {
		edges: number[];
		series: { id: string; label: string; counts: number[] }[];
		c: number;
	}
	let { edges, series, c }: Props = $props();

	const W = 360;
	const H = 220;
	const AX = H / 2;
	const PADL = 0;

	let bins = $derived(edges.length - 1);
	let bw = $derived(W / Math.max(1, bins));
	let max = $derived(Math.max(1, ...series.flatMap((s) => s.counts)));
	// sqrt scale: the extreme bins dominate otherwise
	const h = (n: number) => (Math.sqrt(n) / Math.sqrt(max)) * (AX - 22);

	function zone(i: number): 'yes' | 'no' | 'unclear' {
		const mid = (edges[i] + edges[i + 1]) / 2;
		if (mid >= c) return 'yes';
		if (mid <= 1 - c) return 'no';
		return 'unclear';
	}

	function tally(counts: number[]) {
		const t = { yes: 0, no: 0, unclear: 0 };
		counts.forEach((n, i) => (t[zone(i)] += n));
		return t;
	}

	let exact = $derived(
		edges.some((e) => Math.abs(e - c) < 1e-6) && edges.some((e) => Math.abs(e - (1 - c)) < 1e-6)
	);
	let tallies = $derived(series.map((s) => ({ ...s, t: tally(s.counts) })));
	let x = (p: number) => PADL + p * W;
</script>

<figure>
	<svg viewBox="0 0 {W} {H + 18}" role="img" aria-label="Distribution of the readers' yes-probabilities with the unclear band from {(1 - c).toFixed(2)} to {c.toFixed(2)}">
		<!-- unclear band -->
		<rect x={x(1 - c)} y="0" width={Math.max(0, x(c) - x(1 - c))} height={H} fill="#e3000f" opacity="0.07" />
		{#each tallies as s, si}
			{#each s.counts as n, i}
				{@const hh = h(n)}
				{@const z = zone(i)}
				<rect
					x={x(edges[i]) + 1}
					y={si === 0 ? AX - hh : AX}
					width={bw - 2}
					height={hh}
					class={z}
				/>
			{/each}
		{/each}
		<line x1="0" x2={W} y1={AX} y2={AX} stroke="#000" stroke-width="1" />
		<!-- cutoff markers -->
		<line x1={x(c)} x2={x(c)} y1="0" y2={H} stroke="#e3000f" stroke-width="2" />
		<line x1={x(1 - c)} x2={x(1 - c)} y1="0" y2={H} stroke="#e3000f" stroke-width="2" />
		<text x="2" y="12" class="lab">{series[0]?.label}</text>
		<text x="2" y={H - 4} class="lab">{series[1]?.label}</text>
		<text x="0" y={H + 14} class="tick">0</text>
		<text x={W / 2} y={H + 14} class="tick" text-anchor="middle">0.5</text>
		<text x={W} y={H + 14} class="tick" text-anchor="end">1</text>
		<text x={x(c)} y={H + 14} class="tick red" text-anchor="middle">{c.toFixed(2)}</text>
		{#if c < 0.97}
			<text x={x(1 - c)} y={H + 14} class="tick red" text-anchor="middle">{(1 - c).toFixed(2)}</text>
		{/if}
	</svg>
	<figcaption class="sr-only">p(yes) per fact answer, 20 bins.</figcaption>
</figure>

<table class="tally small num">
	<thead>
		<tr>
			<th scope="col"><span class="sr-only">Reader</span></th>
			<th scope="col"><span class="key yes" aria-hidden="true"></span>Yes</th>
			<th scope="col"><span class="key unclear" aria-hidden="true"></span>Unclear</th>
			<th scope="col"><span class="key no" aria-hidden="true"></span>No</th>
		</tr>
	</thead>
	<tbody>
		{#each tallies as s}
			<tr>
				<th scope="row">{s.label}</th>
				<td>{exact ? '' : '≈'}{s.t.yes}</td>
				<td class="u">{exact ? '' : '≈'}{s.t.unclear}</td>
				<td>{exact ? '' : '≈'}{s.t.no}</td>
			</tr>
		{/each}
	</tbody>
</table>

<style>
	figure {
		margin: 0;
	}
	svg {
		width: 100%;
		height: auto;
		display: block;
		overflow: visible;
	}
	rect.yes {
		fill: #000;
	}
	rect.unclear {
		fill: #e3000f;
	}
	rect.no {
		fill: #bdbdbd;
	}
	.lab {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}
	.tick {
		font-size: 11px;
		fill: #595959;
		font-variant-numeric: tabular-nums;
	}
	.tick.red {
		fill: #c4000d;
		font-weight: 700;
	}
	.tally {
		width: 100%;
		border-collapse: collapse;
		margin-top: 16px;
	}
	.tally th,
	.tally td {
		text-align: right;
		padding: 6px 0;
		border-bottom: var(--hair);
	}
	.tally thead th {
		font-size: var(--t-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		border-bottom: var(--rule);
	}
	.tally th[scope='row'],
	.tally thead th:first-child {
		text-align: left;
		font-weight: 600;
	}
	.tally td.u {
		color: var(--red-ink);
		font-weight: 600;
	}
	.key {
		display: inline-block;
		width: 8px;
		height: 8px;
		margin-right: 6px;
	}
	.key.yes {
		background: #000;
	}
	.key.unclear {
		background: #e3000f;
	}
	.key.no {
		background: #bdbdbd;
	}
</style>
