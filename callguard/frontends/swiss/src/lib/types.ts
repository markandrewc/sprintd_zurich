// Shapes from docs/API.md (contract v1). Only what the UI reads.

export type Label = 'alarm' | 'review' | 'no_alert';
export type FactValue = 'yes' | 'no' | 'unclear';

export interface Family {
	id: string;
	label: string;
	label_de?: string;
	can_alarm?: boolean;
	legal_basis?: string;
}

export interface Reader {
	id: string;
	label: string;
	check?: string;
	model: string;
	model_id?: string | null;
	type?: string | null;
	evidence?: boolean;
	evidence_method?: string | null;
	mode?: string;
	band?: [number, number];
}

export interface Meta {
	app: string;
	api_version: string;
	profile: string;
	runs_dir: string;
	code_version: string;
	models: { asr: string; fact_readers: Reader[]; swiss_german_view: string | null };
	counts: { calls: number; alarm: number; review: number; no_alert: number; reviewed: number };
	families: Family[];
	has_fact_policy: boolean;
	load_errors: string[];
	rulebook?: Rulebook;
}

/** Which rule book decides: the production one (config/policy_table.yaml) or the in-memory demo book. */
export interface Rulebook {
	mode: 'production' | 'demo';
	/** name of the production rule book (profile, e.g. "Sherlock") */
	name: string;
	/** rules of the active book (all / switched on) */
	rules: number;
	enabled: number;
	production: { rules: number; enabled: number };
	editable: boolean;
	can_undo?: boolean;
}

export interface RulebookPut {
	rulebook: Rulebook;
	counts: Counts;
	effect: Effect;
}

export interface CallRow {
	id: string;
	label: Label;
	score: number;
	uncertainty: number;
	family: string | null;
	family_label: string | null;
	reason: string;
	rule_id: string | null;
	legal_basis: string | null;
	passages: number;
	duration: number;
	reviewed: boolean;
	stored_label: Label;
}

export type Counts = Record<Label, number>;

export interface CallsResponse {
	calls: CallRow[];
	counts: Counts;
	total: number;
}

export interface Segment {
	id: string;
	start: number;
	end: number;
	speaker: string;
	role: string;
	text: string;
	confidence?: number;
}

export interface Rule {
	id: string;
	family: string;
	outcome: Label;
	title: string;
	text: string;
	condition: string;
	condition_text: string;
	/** the parsed condition (API); absent in older sample data, then condition_text is parsed */
	condition_tree?: CondNode | null;
	enabled?: boolean;
	position?: number;
	hits?: number;
	hit_calls?: string[];
	report_as?: string | null;
}

/** A rule condition as a tree. A fact test holds when the fact's value is one of `values`. */
export type CondNode =
	| { op: 'and' | 'or'; items: CondNode[] }
	| { op: 'not'; item: CondNode }
	| { op: 'true' }
	| { op: 'fact'; fact: string; label: string; values: FactValue[] };

export interface ReaderAnswer {
	p_yes: number;
	p_no?: number;
	p_unknown?: number;
	value: FactValue;
}

export interface FactAnswer {
	id: string;
	label: string;
	role: string;
	question: string;
	resolved: FactValue;
	agree: boolean;
	combination: string;
	readers: Record<string, ReaderAnswer | null>;
	evidence_segment_ids: string[];
	evidence_reason?: string;
	label_de?: string;
}

export interface Passage {
	index: number;
	start: number;
	end: number;
	family: string;
	family_label: string;
	score: number;
	segment_ids: string[];
	reasons: string[];
	text?: string;
	/** per reason: who found it (Qwen pointing / Kev masking / keyword / pattern) and why */
	sources?: PassageSource[];
	found_by?: string[];
}

export interface PassageSource {
	source: string;
	source_label: string | null;
	method: string | null;
	text: string;
	fact?: string | null;
	/** the rule that this ONE reader's answers matched when it searched (not the call's deciding rule): not shown */
	rule?: string | null;
	/** fact readers: the fact's label, the value and p(yes) this reader gave */
	fact_label?: string | null;
	value?: FactValue | null;
	p_yes?: number | null;
	/** masking reader: p(yes) when this window is removed from the call */
	p_without?: number | null;
	/** pointing reader: its own sentence why this passage shows the fact */
	why?: string | null;
	/** keyword / pattern: what matched */
	phrase?: string | null;
	keyword_id?: string | null;
}

export interface KeywordHit {
	family: string;
	keyword_id: string;
	phrase: string;
	segment_ids: string[];
	start: number;
	end: number;
	score: number;
}

export interface CallDetail {
	id: string;
	duration: number;
	audio_url: string;
	has_audio?: boolean;
	segments: Segment[];
	swiss_german: { description: string; segments: Segment[] } | null;
	decision: {
		label: Label;
		score: number;
		uncertainty: number;
		threshold: number;
		review_floor: number;
		family: string | null;
		family_label: string | null;
		legal_basis: string | null;
		reason: string;
		reasons: string[];
		rule: Rule | null;
		stored_label: Label;
	};
	families: {
		id: string;
		label: string;
		score: number;
		uncertainty: number;
		outcome: Label;
		rule_id: string | null;
		reason: string;
	}[];
	passages: Passage[];
	facts: Record<string, FactAnswer[]>;
	keyword_hits: KeywordHit[];
	reviews: unknown[];
}

export interface Settings {
	/** null: the profile has no fact policy (e.g. sherlock-qwen, the Qwen-only fallback) */
	certainty: number | null;
	combination: string | null;
	/** when the two readers alone would decide differently: rules (default) | review | alarm */
	on_split: string | null;
	threshold: number;
	review_band: number;
	defaults: { certainty: number | null; combination: string | null; threshold: number; on_split: string | null };
	options: {
		certainty: { min: number; max: number; step: number; help: string };
		combination: { id: string; label: string; help: string }[];
		on_split: { id: string; label: string; help: string }[];
		threshold: { min: number; max: number; step: number };
	};
}

export interface Change {
	id: string;
	before: Label;
	after: Label;
}

export interface Effect {
	changed: Change[];
	net: Counts;
	summary: string;
}

export interface SettingsPut {
	settings: Settings;
	counts: Counts;
	changed: Change[];
	elapsed_ms: number;
}

export interface Summary {
	total: number;
	counts: Counts;
	score_histogram: { edges: number[]; alarm: number[]; review: number[]; no_alert: number[] };
	fact_p_yes_histogram: { edges: number[]; [reader: string]: number[] };
	certainty: number | null;
	band: [number, number] | null;
	facts: { answered: number; agree: number; unclear: number };
	by_family: Record<string, Partial<Counts>>;
}

export interface RulesFamily extends Family {
	facts: { id: string; label: string }[];
	rules: Rule[];
}

export interface RulesResponse {
	/** null in demo mode (the demo book is not versioned) */
	version: number | null;
	can_undo: boolean;
	rulebook?: Rulebook;
	families: RulesFamily[];
	cross_rules: Rule[];
}

export interface RuleDraftFact {
	family: string;
	fact: string;
	value: FactValue;
	negate: boolean;
}

export interface RuleDraft {
	facts: RuleDraftFact[];
	join: 'and' | 'or';
	outcome: Label;
	title: string;
	description: string;
	report_as?: string | null;
	author: string;
}

export interface RulePreview {
	rule: Rule;
	hits: string[];
	effect: Effect;
	version?: number;
}

export interface FactDef {
	id: string;
	label: string;
	role: string;
	question: string;
	question_de?: string;
	used_in_rules: number;
	answers: { calls: number; yes: number; no: number; unclear: number; agree: number };
}

export interface Proposal {
	id: number;
	status: string;
	author: string;
	created: string;
	comment: string;
	changes: string[];
	approver?: string;
}

export interface FactsResponse {
	families: (Family & { facts: FactDef[] })[];
	readers: Reader[];
	combination: string;
	active_version: number;
	proposals: Proposal[];
}

export interface Keyword {
	id?: string;
	label: string;
	enabled: boolean;
	case_sensitive: boolean;
	de: string[];
	gsw: string[];
	en: string[];
	harmless: string[] | string;
	hits?: number;
}

export interface KeywordsResponse {
	families: { id: string; label: string; keywords: Keyword[] }[];
}

export interface Step {
	id: string;
	title: string;
	model: string | null;
	description: string;
	phase?: string;
}

export interface ReviewBody {
	verdict: 'violation' | 'no_violation' | 'unclear';
	agree: boolean;
	reasons: string[];
	fact_corrections: Record<string, FactValue>;
	passage_ok: Record<string, boolean>;
	comment: string;
	reviewer: string;
}

export interface ReviewSaved {
	id: string;
	items: number;
	label_seen: Label;
	data_points: number;
	counts: Record<string, number>;
}
