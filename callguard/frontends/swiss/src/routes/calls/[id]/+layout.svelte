<script lang="ts">
	import { page } from '$app/state';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<!-- a fresh page per call: going to the next case starts with an empty review, player and corrections -->
{#key page.params.id}
	{@render children()}
{/key}
