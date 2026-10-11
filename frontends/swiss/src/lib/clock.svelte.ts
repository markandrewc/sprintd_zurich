// Playback clock: follows the <audio> element when it plays, otherwise runs a virtual clock so the
// synced transcript still works when the recording is not on this machine (or with sample data).

export class Clock {
	t = $state(0);
	playing = $state(false);
	rate = $state(1);
	duration = $state(0);
	/** true when the real recording is usable */
	audio = $state(false);
	/** playing one passage: stop when the clock reaches this time (null: play on) */
	stopAt = $state<number | null>(null);
	el: HTMLAudioElement | null = null;
	private raf = 0;
	private last = 0;

	attach(el: HTMLAudioElement | null) {
		this.el = el;
	}

	private loop = (now: number) => {
		if (!this.playing) return;
		if (this.audio && this.el) {
			this.t = this.el.currentTime;
		} else {
			const dt = (now - this.last) / 1000;
			this.t = Math.min(this.duration, this.t + dt * this.rate);
			if (this.t >= this.duration) this.playing = false;
		}
		this.last = now;
		if (this.stopAt !== null && this.t >= this.stopAt) {
			const end = this.stopAt;
			this.pause();
			this.stopAt = null;
			this.seek(end);
			return;
		}
		this.raf = requestAnimationFrame(this.loop);
	};

	/** Play exactly [start, end] and stop at the end (the recording, or the transcript timer without one). */
	playRange(start: number, end: number) {
		this.pause();
		this.seek(start);
		this.stopAt = end;
		this.play();
	}

	play() {
		if (this.playing) return;
		this.playing = true;
		this.last = performance.now();
		if (this.audio && this.el) {
			this.el.playbackRate = this.rate;
			this.el.play().catch(() => {
				// recording not playable: fall back to the virtual clock
				this.audio = false;
			});
		}
		this.raf = requestAnimationFrame(this.loop);
	}

	pause() {
		this.playing = false;
		cancelAnimationFrame(this.raf);
		this.el?.pause();
	}

	toggle() {
		if (this.playing) this.pause();
		else this.play();
	}

	seek(s: number) {
		this.stopAt = null;
		const v = Math.max(0, Math.min(this.duration || s, s));
		this.t = v;
		if (this.audio && this.el) this.el.currentTime = v;
	}

	setRate(r: number) {
		this.rate = r;
		if (this.el) this.el.playbackRate = r;
	}

	ended() {
		this.playing = false;
		this.stopAt = null;
		cancelAnimationFrame(this.raf);
	}

	destroy() {
		cancelAnimationFrame(this.raf);
		this.el?.pause();
	}
}
