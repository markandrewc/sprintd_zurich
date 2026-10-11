import type { Label } from './types';

export const LABEL: Record<Label, string> = {
	alarm: 'Alarm',
	review: 'Review',
	no_alert: 'No alert'
};

export const SQ: Record<Label, string> = { alarm: 'alarm', review: 'review', no_alert: 'none' };
export const O: Record<Label, string> = { alarm: 'o-alarm', review: 'o-review', no_alert: 'o-none' };

export function time(s: number): string {
	if (!isFinite(s) || s < 0) s = 0;
	const m = Math.floor(s / 60);
	const r = Math.floor(s % 60);
	return `${m}:${String(r).padStart(2, '0')}`;
}

export function pct(x: number | undefined | null, digits = 0): string {
	if (x === undefined || x === null || !isFinite(x)) return '–';
	return (x * 100).toFixed(digits);
}

export function p2(x: number | undefined | null): string {
	if (x === undefined || x === null || !isFinite(x)) return '–';
	return x.toFixed(2);
}

export const ROLE: Record<string, string> = {
	advisor: 'Advisor',
	customer: 'Customer',
	act: 'Act',
	context: 'Context',
	exculpatory: 'Exculpatory',
	authorization: 'Authorisation'
};

export function role(r: string | undefined): string {
	if (!r) return '';
	return ROLE[r] ?? r.charAt(0).toUpperCase() + r.slice(1);
}

/** Pull the bare sentence out of an API reason ("... Rule: access.alarm_1.") */
export function stripRule(reason: string, familyLabel?: string | null): string {
	let r = reason.replace(/\s*Rule:\s*\S+\.?\s*$/i, '').trim();
	if (familyLabel && r.startsWith(familyLabel + ':')) r = r.slice(familyLabel.length + 1).trim();
	return r;
}

export function pad2(n: number): string {
	return String(n).padStart(2, '0');
}

/** A rule's name for people: its title, else its sentence; the internal id only as a last resort. */
export function ruleName(r: { id: string; title?: string; text?: string }): string {
	return (r.title || r.text || r.id).trim();
}
