<script lang="ts">
	import { get, post, conn, bump } from '#lib/api.svelte.ts';
	import { role } from '#lib/format.ts';
	import PageHead from '#lib/components/PageHead.svelte';
	import type { FactsResponse, Proposal } from '#lib/types.ts';

	let data = $state<FactsResponse | null>(null);
	let msg = $state<{ text: string; error?: boolean } | null>(null);
	let loadErr = $state('');

	$effect(() => {
		conn.epoch;
		get<FactsResponse>('/api/facts')
			.then((d) => {
				data = d;
				loadErr = '';
			})
			.catch((e) => {
				data = null;
				loadErr = e.status === 400 ? 'Not available for this profile.' : e.message;
			});
	});

	// add form. Four-eyes approval comes once there are real users: for now the fact is proposed and
	// approved in one go, the API still keeps the draft, the approval and the audit entry.
	const AUTO_APPROVER = 'Single-user mode (auto-approved)';
	let formOpen = $state(false);
	let fFamily = $state('');
	let fLabel = $state('');
	let fRole = $state('context');
	let fQuestion = $state('');
	let fComment = $state('');
	let sending = $state(false);
	let formEl = $state<HTMLElement | null>(null);

	function openForm(family = '') {
		fFamily = family || data?.families[0]?.id || '';
		fLabel = '';
		fRole = 'context';
		fQuestion = '';
		fComment = '';
		formOpen = true;
		queueMicrotask(() => formEl?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
	}

	async function add(e: SubmitEvent) {
		e.preventDefault();
		const author = conn.user || 'officer';
		const label = fLabel.trim();
		sending = true;
		let id: number | null = null;
		try {
			const r = await post<{ proposal: Proposal }>('/api/facts/proposals', {
				family: fFamily,
				fact_id: null,
				label,
				role: fRole,
				question: fQuestion.trim(),
				question_de: '',
				author,
				comment: fComment.trim(),
				delete: false
			});
			id = r.proposal.id;
			await post(`/api/facts/proposals/${id}/approve`, { approver: AUTO_APPROVER, note: 'single-user mode' });
			const fam = data?.families.find((f) => f.id === fFamily)?.label ?? fFamily;
			msg = { text: `Fact “${label}” added to ${fam}. Calls get its answer once the AI readers run again.` };
			formOpen = false;
			bump();
		} catch (err: any) {
			// do not leave a half-done draft behind: there is no approval queue to pick it up
			if (id != null) await post(`/api/facts/proposals/${id}/reject`, { user: author, note: 'auto-approve failed' }).catch(() => {});
			msg = { text: err.message, error: true };
		} finally {
			sending = false;
		}
	}

	const ROLES = ['act', 'context', 'exculpatory', 'authorization'];
</script>

<svelte:head><title>Facts · Sherlock Phones</title></svelte:head>

<PageHead n="03 Settings" title="Facts" lead="The yes/no questions both AI readers answer for every call.">
	<button class="btn primary" onclick={() => openForm()}>Add a fact</button>
</PageHead>

{#if loadErr}
	<div class="msg err" role="status">
		<p><b>{loadErr}</b></p>
	</div>
{/if}

{#if msg}
	<div class="msg" class:err={msg.error} role="status">
		<p><b>{msg.text}</b></p>
		<button class="btn link small" onclick={() => (msg = null)}>Close</button>
	</div>
{/if}

{#if formOpen}
	<section class="grid form" bind:this={formEl} aria-labelledby="pf-h">
		<div class="qh">
			<h2 id="pf-h" class="h2">New fact</h2>
		</div>
		<form class="pf" onsubmit={add}>
			<label><span class="label">Category</span>
				<select class="field" bind:value={fFamily}>
					{#each data?.families ?? [] as f}<option value={f.id}>{f.label}</option>{/each}
				</select>
			</label>
			<label><span class="label">Short name</span><input class="field" bind:value={fLabel} required /></label>
			<label class="wide"><span class="label">Question for the readers (yes / no)</span><textarea class="field" rows="3" bind:value={fQuestion} required></textarea></label>
			<fieldset>
				<legend class="label">Role</legend>
				<div class="seg">
					{#each ROLES as r}<label><input type="radio" bind:group={fRole} value={r} /><span>{role(r)}</span></label>{/each}
				</div>
			</fieldset>
			<label class="wide"><span class="label">Why <span class="muted">optional</span></span><input class="field" bind:value={fComment} /></label>
			<div class="wide fa">
				<button class="btn primary" type="submit" disabled={sending}>{sending ? 'Adding…' : 'Add fact'}</button>
				<button class="btn" type="button" onclick={() => (formOpen = false)}>Cancel</button>
			</div>
		</form>
	</section>
{/if}

{#each data?.families ?? [] as fam, fi}
	<section class="grid fam" aria-labelledby="ff-{fam.id}">
		<div class="fh">
			<p class="label muted num">{String(fi + 1).padStart(2, '0')}</p>
			<h2 id="ff-{fam.id}" class="h2">{fam.label}</h2>
			<button class="btn link small" onclick={() => openForm(fam.id)}>+ Add fact</button>
		</div>
		<table class="ft">
			<thead>
				<tr>
					<th scope="col">Fact</th>
					<th scope="col" class="r">Role</th>
					<th scope="col" class="dist">Answers on {fam.facts[0]?.answers.calls ?? 0} calls</th>
					<th scope="col" class="r">Agree</th>
					<th scope="col" class="r">Rules</th>
				</tr>
			</thead>
			<tbody>
				{#each fam.facts as f (f.id)}
					{@const a = f.answers}
					<tr>
						<td>
							<p class="fl">{f.label}</p>
							<p class="small muted q">{f.question}</p>
						</td>
						<td class="r small">{role(f.role)}</td>
						<td class="dist">
							<span class="stack" role="img" aria-label="{a.yes} yes, {a.unclear} unclear, {a.no} no">
								<span class="y" style="flex:{a.yes}"></span><span class="u" style="flex:{a.unclear}"></span><span class="n" style="flex:{a.no}"></span>
							</span>
							<span class="small num nums"><b>{a.yes}</b> yes · <b class="red">{a.unclear}</b> unclear · {a.no} no</span>
						</td>
						<td class="r num">{a.agree}/{a.calls}</td>
						<td class="r num">{f.used_in_rules}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>
{/each}

<style>
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
	.form {
		margin-top: 48px;
		align-items: start;
		scroll-margin-top: 120px; /* below the sticky header */
	}
	.qh {
		grid-column: 1 / span 3;
	}
	.pf {
		grid-column: 4 / span 9;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 24px;
		border-top: 4px solid var(--red);
		padding-top: 16px;
	}
	.pf .wide {
		grid-column: 1 / -1;
	}
	.pf fieldset {
		border: 0;
		padding: 0;
		margin: 0;
	}
	.pf legend {
		margin-bottom: 8px;
	}
	.fa {
		display: flex;
		gap: 12px;
		align-items: center;
	}

	.fam {
		margin-top: 64px;
		align-items: start;
	}
	.fh {
		grid-column: 1 / span 3;
	}
	.fh .h2 {
		margin: 4px 0 8px;
	}
	.ft {
		grid-column: 4 / span 9;
		border-collapse: collapse;
		width: 100%;
	}
	.ft th {
		text-align: left;
		font-size: var(--t-xs);
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		padding: 8px 12px 8px 0;
		border-bottom: var(--rule);
	}
	.ft td {
		padding: 14px 12px 14px 0;
		border-bottom: var(--hair);
		vertical-align: top;
	}
	.r {
		text-align: right !important;
		white-space: nowrap;
	}
	.fl {
		font-weight: 600;
	}
	.q {
		max-width: 60ch;
		margin-top: 2px;
	}
	.dist {
		width: 220px;
	}
	.stack {
		display: flex;
		height: 10px;
		background: var(--grey-1);
		margin-top: 6px;
	}
	.stack .y {
		background: var(--black);
	}
	.stack .u {
		background: var(--red);
	}
	.stack .n {
		background: var(--grey-2);
	}
	.nums {
		display: block;
		margin-top: 6px;
		font-size: var(--t-xs);
	}

	@media (max-width: 1100px) {
		.qh,
		.pf,
		.fh,
		.ft {
			grid-column: 1 / span 12;
			margin-top: 16px;
		}
	}
</style>
