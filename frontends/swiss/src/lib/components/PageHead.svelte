<script lang="ts">
	import type { Snippet } from 'svelte';
	interface Props {
		n: string;
		title: string;
		lead?: string;
		children?: Snippet;
	}
	let { n, title, lead, children }: Props = $props();
</script>

<header class="grid ph">
	<p class="n label">{n}</p>
	<div class="t">
		<h1 class="display">{title}</h1>
		{#if lead}<p class="lead">{lead}</p>{/if}
	</div>
	<div class="aside">
		{@render children?.()}
	</div>
</header>

<style>
	.ph {
		padding-bottom: 32px;
		border-bottom: var(--rule-thick);
		align-items: end;
	}
	.n {
		grid-column: 1 / span 2;
		align-self: start;
		padding-top: 12px;
	}
	.t {
		grid-column: 3 / span 6;
	}
	.lead {
		margin-top: 16px;
		font-size: var(--t-l);
		line-height: 1.35;
		max-width: 36ch;
	}
	.aside {
		grid-column: 9 / span 4;
		justify-self: end;
		text-align: right;
	}
	@media (max-width: 1100px) {
		.n,
		.t,
		.aside {
			grid-column: 1 / span 12;
			justify-self: start;
			text-align: left;
		}
		.aside {
			margin-top: 16px;
		}
	}
</style>
