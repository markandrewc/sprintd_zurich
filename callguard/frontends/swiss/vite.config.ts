import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// The API (callguard api) runs on 8600. Proxying keeps audio + fetch same-origin.
const API = process.env.SHERLOCK_API ?? 'http://localhost:8600';
const proxy = { '/api': { target: API, changeOrigin: true } };

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter()
		})
	],
	server: { port: 8605, strictPort: true, proxy },
	preview: { port: 8605, strictPort: true, proxy }
});
