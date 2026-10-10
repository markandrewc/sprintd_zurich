"""Re-evaluate policy-table variants on cached fact probabilities (no LLM). Dev calls only."""
import json, sys, copy
from callguard.checks.facts import parse_policy_table, discretize
import yaml
RES = 'runs/experiments/llm_models/qwen25_7b/results.jsonl'
ROWS = 'runs/experiments/llm_models/qwen25_7b__facts_only/rows.json'
exp = {r['call_id']: r for r in json.load(open(ROWS))['fixed']}
calls = {}
for line in open(RES):
    d = json.loads(line)
    f = d['checks']['facts']['family_scores']
    calls[d['call_id']] = {fam: {k: v['p'] for k, v in fs['detail']['facts'].items()} for fam, fs in f.items()}
    calls[d['call_id']]['_patterns'] = d['checks'].get('patterns', {}).get('family_scores', {})
base_raw = yaml.safe_load(open('config/policy_table.yaml'))
ORDER = {'alarm': 2, 'review': 1, 'no_alert': 0}

def run(raw, post=None, name=''):
    t = parse_policy_table(raw)
    out = {}
    for cid, fams in calls.items():
        best = 'no_alert'; why = None
        for fam, probs in fams.items():
            if fam.startswith('_'): continue
            vals = {k: discretize(p) for k, p in probs.items()}
            r = t.families[fam].decide(vals)
            lab = r.label if r else 'no_alert'
            if post: lab = post(cid, fam, probs, vals, lab)
            if ORDER[lab] > ORDER[best]: best, why = lab, fam
        out[cid] = (best, why)
    flag = lambda l: l != 'no_alert'
    pos = [c for c in out if flag(exp[c]['expected'])]; neg = [c for c in out if not flag(exp[c]['expected'])]
    far = sum(flag(out[c][0]) for c in neg) / len(neg); miss = sum(not flag(out[c][0]) for c in pos) / len(pos)
    acc = sum(out[c][0] == exp[c]['expected'] for c in out) / len(out)
    rv = [c for c in out if exp[c]['expected'] == 'review']
    rrec = sum(out[c][0] == 'review' for c in rv) / len(rv)
    print(f"{name:34s} FAR {far:.0%} ({sum(flag(out[c][0]) for c in neg)}/{len(neg)})  miss {miss:.0%} ({sum(not flag(out[c][0]) for c in pos)}/{len(pos)})  3cls {acc:.0%}  review-recall {rrec:.0%}")
    errs = [f"{c.replace('Stufe','S')}:{exp[c]['expected'][:2]}->{out[c][0][:2]}" for c in sorted(out) if out[c][0] != exp[c]['expected']]
    print('    errors:', ' '.join(errs))
    return out

base = run(base_raw, name='base (current table)')

# V1: disclosure open authorization = neither confirmed (authorized != yes) -> review when a third-party request exists
v1 = copy.deepcopy(base_raw)
for r in v1['families']['disclosure']['rules']:
    if r['id'] == 'disclosure.review_2':
        r['when'] = 'third_party_request = yes and authorized != yes'
run(v1, name='V1 disclosure: request & !authorized')

# V2: exculpatory conflict -> review (alarm parts yes, exculpatory yes but p<0.9)
CONFLICT = {'trade': (['wish', 'inside_info'], 'public'), 'access': (['spoken', 'current'], 'expired_or_sample'),
            'documentation': (['omit_request', 'relevant'], 'correction_or_private'),
            'splitting': (['split_request', 'avoid_control'], 'harmless')}
def post_conflict(cid, fam, probs, vals, lab, hi=0.9):
    if lab == 'no_alert' and fam in CONFLICT:
        acts, ex = CONFLICT[fam]
        if all(vals[a] == 'yes' for a in acts) and vals[ex] == 'yes' and probs[ex]['yes'] < hi:
            return 'review'
    return lab
run(base_raw, post_conflict, name='V2 exculpatory conflict (<0.9)->review')

# V3: pattern anchor: patterns found a digit run (access score>0.5) but facts spoken=no -> review
def post_anchor(cid, fam, probs, vals, lab):
    if fam == 'access' and lab == 'no_alert':
        p = calls[cid]['_patterns'].get('access') or {}
        if (p.get('score') or 0) >= 0.5 and vals['spoken'] != 'yes':
            return 'review'
    return lab
run(base_raw, post_anchor, name='V3 pattern-anchor disagreement->review')

# V4: decide_at sweep proxies: unclear if max<0.6 / 0.7
for da in (0.6, 0.7):
    t = parse_policy_table(base_raw)
    def post_da(cid, fam, probs, vals, lab, da=da):
        v2 = {k: discretize(p, da) for k, p in probs.items()}
        r = t.families[fam].decide(v2); return r.label if r else 'no_alert'
    run(base_raw, post_da, name=f'V4 decide_at={da}')

# V5: review if act fact NOT ruled out (p(no)<0.35 and not yes) - generic "act open"
ACT = {'trade': 'wish', 'access': 'spoken', 'disclosure': 'data_given', 'documentation': 'omit_request', 'splitting': 'split_request'}
def post_actopen(cid, fam, probs, vals, lab, lim=0.35):
    if lab == 'no_alert' and vals[ACT[fam]] == 'unclear' and probs[ACT[fam]]['no'] < lim:
        return 'review'
    return lab
run(base_raw, post_actopen, name='V5 act open (p_no<0.35)->review')

def combo(cid, fam, probs, vals, lab):
    for f in (post_conflict, post_anchor):
        lab = f(cid, fam, probs, vals, lab)
    return lab
run(v1, combo, name='V1+V2+V3')

# p(unclear) mass as a review score: AUC review vs rest of max over families of mean p(unclear) of act+context facts
import itertools
def auc(pos, neg):
    s = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg); return s / (len(pos) * len(neg))
pt = parse_policy_table(base_raw)
sc = {}
for cid, fams in calls.items():
    m = 0
    for fam, probs in fams.items():
        if fam.startswith('_'): continue
        ids = [f.id for f in pt.families[fam].facts if f.role in ('act', 'context')]
        m = max(m, sum(probs[i]['unclear'] for i in ids) / len(ids))
    sc[cid] = m
rv = [sc[c] for c in calls if exp[c]['expected'] == 'review']; nrv = [sc[c] for c in calls if exp[c]['expected'] != 'review']
print('AUC review-vs-rest of max-family mean p(unclear) [act+context]:', round(auc(rv, nrv), 2), 'review:', [round(x, 2) for x in rv])

print('--- p(unclear) score, sorted')
for c in sorted(sc, key=lambda c: -sc[c])[:16]:
    print(f"  {c:16s} {exp[c]['expected']:8s} {sc[c]:.2f}")
for c in ['Stufe2_C09-K3', 'Stufe2_C09-K4', 'Stufe1_D05-K2', 'Stufe2_C10-K3', 'Stufe3_C17-K3']:
    print(c, {k: (v.get('score'), v.get('verdict')) for k, v in calls[c]['_patterns'].items()})

def post_anchor2(cid, fam, probs, vals, lab):
    if fam == 'access' and lab == 'no_alert':
        p = calls[cid]['_patterns']
        if max((p.get(k) or {}).get('score') or 0 for k in ('access', 'numbers')) > 0 and vals['spoken'] != 'yes':
            return 'review'
    return lab
print('---')
run(base_raw, post_anchor2, name='V3b digit-run anchor & spoken!=yes')
print([ (c, calls[c]['_patterns'].get('numbers', {}).get('score')) for c in calls if (calls[c]['_patterns'].get('numbers') or {}).get('score')])
def post_anchor3(cid, fam, probs, vals, lab):
    if fam == 'access' and lab == 'no_alert':
        p = calls[cid]['_patterns']
        if max((p.get(k) or {}).get('score') or 0 for k in ('access', 'numbers')) >= 0.2 and vals['spoken'] != 'yes':
            return 'review'
    return lab
print('===')
run(base_raw, post_anchor3, name='V3c digit-run(>=0.2) & spoken!=yes')
def combo2(cid, fam, probs, vals, lab):
    for f in (post_conflict, post_anchor3):
        lab = f(cid, fam, probs, vals, lab)
    return lab
run(v1, combo2, name='V1+V2+V3c')
print('#####')
# clean/noisy decision consistency per dialogue (base)
from collections import defaultdict
dd = defaultdict(dict)
for c, (lab, fam) in base.items():
    dd[exp[c]['dialogue_id']][exp[c]['noisy']] = lab
inc = [d for d, v in dd.items() if len(set(v.values())) > 1]
print('inconsistent clean/noisy dialogues (base):', len(inc), '/', len(dd), inc)
# act-gated cascade: skip non-act facts when act p(no) >= 0.9 (except disclosure: third_party_request also gate)
GATE = {'trade': ['wish'], 'access': ['spoken'], 'disclosure': ['data_given', 'third_party_request'], 'documentation': ['omit_request'], 'splitting': ['split_request']}
tot = asked = 0
for cid, fams in calls.items():
    for fam, probs in fams.items():
        if fam.startswith('_'): continue
        n = len(probs); tot += n
        if all(probs[g]['no'] >= 0.9 for g in GATE[fam]): asked += len(GATE[fam])
        else: asked += n
print(f'cascade: fact prompts {asked}/{tot} = {asked/tot:.0%}')
print('@@@@@')
t = parse_policy_table(base_raw)
from collections import Counter
fp = Counter(); n = Counter()
for cid, fams in calls.items():
    for fam, probs in fams.items():
        if fam.startswith('_') or fam == exp[cid]['expected_family']: continue
        vals = {k: discretize(p) for k, p in probs.items()}
        r = t.families[fam].decide(vals); n[fam] += 1
        if r and r.label != 'no_alert': fp[fam] += 1; print('  cross-family flag:', cid, fam, r.id)
print('cross-family negatives flagged:', dict(fp), 'of', dict(n))
