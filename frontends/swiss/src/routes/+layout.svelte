<script lang="ts">
	import '@fontsource-variable/inter';
	import '../app.css';
	import { page } from '$app/state';
	import { conn, probe, setUser, bump, refreshRulebook, setRulebook, FORCE_FIXTURES } from '#lib/api.svelte.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	probe();

	// API down: keep looking for it and reload the page data when it is back (never sample data instead)
	$effect(() => {
		const id = setInterval(async () => {
			if (conn.mode !== 'down') return;
			await probe();
			if ((conn.mode as string) === 'live') bump();
		}, 10000);
		return () => clearInterval(id);
	});

	const nav = [
		{ href: '/', n: '01', t: 'Calls' },
		{ href: '/settings/rules', n: '02', t: 'Rules' },
		{ href: '/settings/facts', n: '03', t: 'Facts' },
		{ href: '/settings/keywords', n: '04', t: 'Keywords' },
		{ href: '/how', n: '05', t: 'How it works' }
	];

	function active(href: string) {
		const p = page.url.pathname;
		return href === '/' ? p === '/' || p.startsWith('/calls') : p.startsWith(href);
	}

	let name = $state(conn.user);

	// which rule book decides: re-read whenever anything changed (a rule added, a switch)
	$effect(() => {
		conn.epoch;
		if (conn.mode === 'live') refreshRulebook();
	});
	let rb = $derived(conn.rulebook);
	const regeln = (n: number) => `${n} ${n === 1 ? 'rule' : 'rules'}`;

	let switching = $state(false);
	let switchMsg = $state<{ text: string; title?: string; err?: boolean } | null>(null);
	let toastT: ReturnType<typeof setTimeout>;
	async function applyOurs() {
		switching = true;
		clearTimeout(toastT);
		try {
			const r = await setRulebook('production');
			const n = r.effect.changed.length;
			switchMsg = { text: `${n} ${n === 1 ? 'call' : 'calls'} changed`, title: r.effect.summary };
			toastT = setTimeout(() => (switchMsg = null), 8000);
		} catch (e: any) {
			switchMsg = { text: e.message, err: true };
		} finally {
			switching = false;
		}
	}

	// the sticky header's height, for sticky blocks and scroll targets below it
	let headH = $state(0);
	$effect(() => {
		if (headH) document.documentElement.style.setProperty('--head-h', `${headH}px`);
	});

	let retrying = $state(false);
	async function retry() {
		retrying = true;
		await probe();
		retrying = false;
		if ((conn.mode as string) === 'live') bump();
	}
</script>

<svelte:head>
	<title>Sherlock Phones</title>
	<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png" />
	<link rel="icon" type="image/png" sizes="64x64" href="/favicon-64.png" />
	<link rel="apple-touch-icon" href="/logo.png" />
</svelte:head>

<a class="skip" href="#main">Skip to content</a>

<header class="wrap" bind:offsetHeight={headH}>
	<div class="grid top">
		<a class="mark" href="/" aria-label="Sherlock Phones, calls">
			<img class="logo" src="/logo.png" alt="" width="48" height="48" />
			<span class="word">Sherlock<br />Phones</span>
		</a>
		<nav aria-label="Main">
			<ul>
				{#each nav as item}
					<li>
						<a href={item.href} class:on={active(item.href)} aria-current={active(item.href) ? 'page' : undefined}>
							<span class="n">{item.n}</span>
							<span class="t">{item.t}</span>
						</a>
					</li>
				{/each}
			</ul>
		</nav>
		<div class="who">
			<label class="label muted" for="who">Officer</label>
			<input
				id="who"
				class="field small"
				placeholder="Your name"
				bind:value={name}
				onchange={() => setUser(name.trim())}
			/>
			{#if conn.mode === 'fixtures'}
				<span class="src fx"><span class="dot" aria-hidden="true"></span>Sample data</span>
			{:else if conn.mode === 'down'}
				<button class="src fx" onclick={retry}><span class="dot" aria-hidden="true"></span>API down</button>
			{:else if conn.mode === 'live'}
				<span
					class="src live"
					title={conn.source ? `Live results · profile ${conn.source.profile} · ${conn.source.runs_dir} · ${conn.source.calls} calls` : 'Live results'}
				>
					<span class="dot" aria-hidden="true"></span>Live
					{#if rb?.editable && rb.mode === 'production'}
						<a class="rb" href="/settings/rules" title="Which rule book decides the calls">· Rule book {rb.name} ({rb.rules})</a>
					{/if}
				</span>
			{/if}
		</div>
	</div>
</header>

{#if conn.mode === 'down'}
	<div class="banner down" role="alert">
		<div class="wrap">
			<p><b>API not reachable.</b> Retrying every 10 s.</p>
			<p class="small" title={conn.error}><code>uv run callguard api -c sherlock --set paths.runs_dir=&lt;run folder&gt; --port 8600</code></p>
			<button class="btn small" onclick={retry} disabled={retrying}>{retrying ? 'Trying…' : 'Retry now'}</button>
		</div>
	</div>
{:else if conn.mode === 'live' && rb?.mode === 'demo'}
	<div class="banner demo" role="status">
		<div class="wrap db">
			<p title="In memory only: the rule book file is not changed. Calls are re-decided from the stored fact answers.">
				<b>Demo rule book</b> · <a href="/settings/rules">{regeln(rb.rules)}</a>
			</p>
			<button class="btn small" onclick={applyOurs} disabled={switching}>{switching ? 'Applying…' : 'Apply our rule book'}</button>
		</div>
	</div>
{:else if conn.mode === 'fixtures' || FORCE_FIXTURES}
	<div class="banner sample" role="status">
		<div class="wrap">
			<p><b>Sample data.</b> Nothing is saved.</p>
		</div>
	</div>
{/if}

{#if switchMsg}
	<div class="toast" class:err={switchMsg.err} role="status" title={switchMsg.title}>
		<p><b>{switchMsg.text}</b></p>
		<button class="x" onclick={() => (switchMsg = null)} aria-label="Close">×</button>
	</div>
{/if}

<main id="main" class="wrap">
	{@render children()}
</main>

<footer class="wrap">
	<div class="grid foot">
		<p class="label">Sherlock Phones</p>
		<p class="small muted">Decision support. An officer decides.</p>
	</div>
</footer>

<style>
	.skip {
		position: absolute;
		left: -9999px;
	}
	.skip:focus {
		left: 16px;
		top: 16px;
		background: var(--black);
		color: var(--white);
		padding: 8px 12px;
		z-index: 10;
	}

	header {
		padding-top: 24px;
		padding-bottom: 24px;
		border-bottom: var(--rule);
		position: sticky;
		top: 0;
		background: var(--white);
		z-index: 5;
	}

	.top {
		align-items: start;
	}

	.mark {
		grid-column: 1 / span 3;
		display: flex;
		gap: 12px;
		align-items: flex-start;
	}
	.mark:hover {
		text-decoration: none;
	}
	.logo {
		width: 48px;
		height: 48px;
		flex: none;
		margin-top: -8px;
	}
	.word {
		font-weight: 700;
		font-size: 17px;
		line-height: 1;
		letter-spacing: -0.02em;
	}

	nav {
		grid-column: 4 / span 6;
	}
	nav ul {
		display: grid;
		grid-template-columns: repeat(5, auto);
		justify-content: start;
		column-gap: 28px;
	}
	nav a {
		display: block;
		font-size: var(--t-s);
		font-weight: 600;
		line-height: 1.2;
		padding-bottom: 4px;
		border-bottom: 3px solid transparent;
	}
	nav a:hover {
		text-decoration: none;
		border-bottom-color: var(--black);
	}
	nav a.on {
		border-bottom-color: var(--red);
	}
	nav .n {
		display: block;
		font-size: var(--t-xs);
		color: var(--grey-ink);
		font-weight: 500;
	}

	.who {
		grid-column: 10 / span 3;
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		column-gap: 12px;
	}
	.who .field {
		padding: 4px 0;
		border-bottom-width: 1px;
	}

	.src {
		font-size: var(--t-xs);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		white-space: nowrap;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: 0;
		padding: 0;
	}
	.src.fx {
		color: var(--red-ink);
		cursor: pointer;
	}
	.dot {
		width: 8px;
		height: 8px;
		background: currentColor;
		display: inline-block;
	}
	.src.live .dot {
		background: var(--black);
	}

	.who .src {
		grid-column: 1 / -1;
		margin-top: 8px;
		white-space: normal;
	}
	.banner {
		padding: 10px 0;
		color: var(--white);
	}
	.banner.down {
		background: var(--red);
	}
	.banner.sample {
		background: var(--black);
	}
	.banner.demo {
		background: var(--black);
		border-bottom: 4px solid var(--red);
	}
	.banner.demo a {
		color: var(--white);
		text-decoration: underline;
	}
	.db {
		display: flex;
		flex-wrap: wrap;
		gap: 12px 24px;
		align-items: center;
		justify-content: space-between;
	}
	.db .btn {
		margin-top: 0;
		flex: none;
	}
	.toast {
		position: fixed;
		right: 24px;
		bottom: 24px;
		z-index: 20;
		display: flex;
		gap: 16px;
		align-items: center;
		background: var(--black);
		color: var(--white);
		padding: 14px 16px 14px 20px;
		border-left: 6px solid var(--red);
		font-size: var(--t-l);
	}
	.toast.err {
		background: var(--red);
	}
	.toast .x {
		background: none;
		border: 0;
		color: var(--white);
		font-size: 22px;
		line-height: 1;
		cursor: pointer;
	}
	.rb {
		color: var(--grey-ink);
		font-weight: 500;
		letter-spacing: 0;
		text-transform: none;
		white-space: nowrap;
	}
	.banner p + p {
		margin-top: 4px;
	}
	.banner code {
		font-size: 0.95em;
		overflow-wrap: anywhere;
	}
	.banner .btn {
		margin-top: 6px;
		background: var(--white);
		color: var(--black);
	}
	main {
		padding-top: 32px;
		padding-bottom: 120px;
		min-height: 70vh;
	}

	footer {
		border-top: var(--rule);
		padding-top: 16px;
		padding-bottom: 32px;
	}
	.foot p:first-child {
		grid-column: 1 / span 3;
	}
	.foot p:last-child {
		grid-column: 4 / span 9;
	}

	@media (max-width: 1100px) {
		.mark {
			grid-column: 1 / span 12;
			margin-bottom: 16px;
		}
		nav {
			grid-column: 1 / span 12;
		}
		nav ul {
			grid-template-columns: repeat(3, auto);
			row-gap: 8px;
		}
		.who {
			grid-column: 1 / span 12;
			margin-top: 12px;
		}
	}
</style>
