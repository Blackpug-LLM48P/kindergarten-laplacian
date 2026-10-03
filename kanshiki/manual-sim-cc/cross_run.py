"""前回（_sealed_prior）と今回の突き合わせ。対応表は実行者が§2の基準で作成（ALIGN）。"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent; P=ROOT/'_sealed_prior'
def load(p): return json.loads(Path(p).read_text())
cur_ref=load(ROOT/'reference.json'); pri_ref=load(P/'reference.json')
def accepted(ref): return {g['ref_id']:dict(g,input_id=i['input_id']) for i in ref['inputs'] for g in i['groups'] if g['status']=='accepted' and not g['rule_excluded']}
CA,PA=accepted(cur_ref),accepted(pri_ref)
# (今回, 前回, 理由)
ALIGN=[
 ('Q005-R1','Q005-R07','前日の衣装貸与と、本人が別装束で戦い脾腹を貫かれる結末の対応。両者とも負傷文を必要根拠にし、教訓で回収しない点を含む。A側引用は異なるが同じ関係。'),
 ('Q005-R3','Q005-R03','同じ戦闘で、敵が猩々緋の姿に結びつける『鎗中村』像と、黒皮縅の実際の新兵衛への反応を区別する関係。うらみの文が共通の必要根拠。'),
 ('Q005-R4','Q005-R06','『猩々緋の武者』の正体が、本人の黒皮縅への装束替えで確定する関係。『その日に限って、黒皮縅』が共通の必要根拠。'),
 ('Q008-R1','Q008-R01','母のうなぎの希望はごんの推測として示され、償いの動機になる関係。引用が同一。（前回R07の観察／推論の区別は、今回R1の命題の一部とも重なるが、一対一ではR01に対応させた）'),
 ('Q008-R2','Q008-R04','第六節の同じ来訪で、ごんの意図（栗）と兵十の認識（いたずら）の情報差が誤射に結びつく関係。『ごん狐めが、またいたずら』が共通の必要根拠。'),
 ('Q008-R3','Q008-R05','結末を発砲直後の銃と煙の像で閉じる関係。煙の文が共通の必要根拠。'),
 ('Q008-R4','Q008-R02','いわしの投げ入れに対する、ごんの評価と兵十が受けた結果（独り言で原因が判明）の関係。兵十の同じ独り言が必要根拠。'),
 ('Q010-R2','Q010-R05','『しかしそれだけでは…』の留保と『頭が悪いと同時に頭がよくなくてはならない』の小結の関係。引用が同一（順序のみ逆）。'),
 ('Q010-R3','Q010-R02','『頭のいい人は』の反復が段落ごとに別の論点（研究局面）を導入する関係。前回R03（道・進行の比喩の一貫）とも引用範囲が近いが、命題（反復が別論点を導入）はR02と同じ。'),
 ('Q007-R1','Q007-R01','42.7%→49.7%の増加と結論の『7.0ポイント低下』の不両立。両方problem。'),
 ('Q017-R1','Q017-R01','42.7%→49.7%と結論の『7.0ポイント上昇』の対応。両方function。'),
]
NOT_ALIGNED_NOTES={
 'Q005-R2':'『形』の語の役割変化（戒め→誇り）。前回R04・R05はA側に誇りの文を共有するが、比較対象（敵の反応／後悔）が異なり対応させない。',
 'Q013-R1':'主文のＢ・Ｃ額がＡのちょうど半額で請求額と対応。前回R04（主文Ｂ＝Ｃ）・R01（原審額と減縮額）と一部重なるが、必要根拠・命題が一意に対応しないため対応させない（alignment_ambiguous相当）。',
 'Q012-R2':'二命題が『ある意味では』で条件限定され矛盾でない。前回は同じ関係をsplit（Q012-R01）とし、採択R02は命題の扱いと解説の焦点（別根拠）。',
 'Q010-R1':'老科学者の語りとしての枠付けと『世迷い言』での相対化。前回は末尾の読者反応の分類をsplit（Q010-R06）とし、枠付け自体の採択群はない。',
 'Q019-R1':'脚注24に対応する参照記号の欠落（problem）。前回の3注釈者はいずれも注釈していない。',
 'Q007-R2':'同上（脚注24）。','Q017-R2':'同上（脚注24）。','Q013-R2':'日付の段落間整合。前回に対応する群なし。','Q008-R5':'冒頭の伝聞枠と『そうです』による伝達層。前回に対応する群なし。',
 'Q019-R01':'前回function：42.7→49.7の増加記述と数値の対応。今回は注釈なし（Q017の結論との対応はQ017-R1で採択）。',
 'Q019-R02':'前回function：脚注23の単純比較の留保。今回は注釈なし。','Q007-R02':'同上（脚注23の留保）。','Q017-R02':'同上（脚注23の留保）。',
 'Q019-R05':'前回function：4か国の影響認識の比較。今回は同じ総括をunresolvedとして棄却・RULE該当（Q019-R2）。','Q007-R05':'同上（今回Q007-R4）。','Q017-R05':'同上（今回Q017-R4）。',
}
mC={c for c,p,_ in ALIGN}; mP={p for c,p,_ in ALIGN}
assert mC<=set(CA) and mP<=set(PA) and len(mC)==len(ALIGN)==len(mP)
qs=json.loads((ROOT/'plan.json').read_text())['selected']
byq=[]
for q in qs:
    c=[k for k,v in CA.items() if v['input_id']==q]; p=[k for k,v in PA.items() if v['input_id']==q]
    m=[a for a in ALIGN if CA[a[0]]['input_id']==q]
    byq.append(dict(input_id=q,current=len(c),prior=len(p),matched=len(m),
        current_only=[dict(ref_id=k,polarity=CA[k]['polarity'],note=NOT_ALIGNED_NOTES.get(k,'')) for k in sorted(set(c)-mC)],
        prior_only=[dict(ref_id=k,polarity=PA[k]['polarity'],note=NOT_ALIGNED_NOTES.get(k,'')) for k in sorted(set(p)-mP)]))
M=len(ALIGN);nc,np_=len(CA),len(PA)
pol=sum(CA[c]['polarity']==PA[p]['polarity'] for c,p,_ in ALIGN)
ref_cmp=dict(n_current=nc,n_prior=np_,matched=M,dice=2*M/(nc+np_),jaccard=M/(nc+np_-M),polarity_agreement=f'{pol}/{M}',
  current_problem=[k for k,v in CA.items() if v['polarity']=='problem'],prior_problem=[k for k,v in PA.items() if v['polarity']=='problem'],
  status_counts=dict(current=load(ROOT/'agreement.json')['group_status_counts'],prior=load(P/'agreement.json')['group_status_counts']),
  annotations=dict(current=load(ROOT/'agreement.json')['raw_annotations'],prior=load(P/'agreement.json')['raw_annotations']),
  annotator_pairs=dict(current=[{k:x[k] for k in ('pair','n_a','n_b','matches','dice','jaccard','polarity_agreement','item_set_agreement')} for x in load(ROOT/'agreement.json')['pairs']],
                       prior=[{k:x[k] for k in ('pair','n_a','n_b','matches','dice','jaccard','polarity_agreement','item_set_agreement')} for x in load(P/'agreement.json')['pairs']]),
  alignment=[dict(current=c,prior=p,polarity=[CA[c]['polarity'],PA[p]['polarity']],reason=r) for c,p,r in ALIGN],by_input=byq)
# 監査の一致（主監査、条件はoperator-output-mapで解決）
def audits(root):
    mp={(m['input_id'],m['output_alias']):m['condition'] for m in load(root/'operator-output-map.json')}
    out={}
    for f in sorted((root/'audit-validation').glob('primary-*.json')):
        for i in load(f)['inputs']:
            for o in i['outputs']:
                out[(i['input_id'],mp[(i['input_id'],o['output_alias'])])]={r['ref_id']:sorted(set(r['events'])) for r in o['correspondence']}
    return out
CAu,PAu=audits(ROOT),audits(P)
rows=[];agree={'v5':[0,0],'B2':[0,0]}
for c,p,_ in ALIGN:
    q=CA[c]['input_id']
    for cond in ('v5','B2'):
        ce,pe=CAu[(q,cond)][c],PAu[(q,cond)][p]
        same=ce==pe; agree[cond][0]+=same; agree[cond][1]+=1
        rows.append(dict(input_id=q,condition=cond,current_ref=c,prior_ref=p,current_events=ce,prior_events=pe,same=same))
audit_cmp=dict(scope='両実行で対応した採択参照（11）について、主監査の挙動フラグ集合の一致',
  agreement={k:f'{a}/{n}' for k,(a,n) in agree.items()},rows=rows)
# 主指標
cm,pm=load(ROOT/'metrics.json'),load(P/'metrics.json')
def pooled(m,cond,key):
    x=m['pooled_alternative'][cond][key]; return dict(n=x['n'],den=x['denominator'],rate=x['rate'])
KEYS=['DET','PEND','HOLD','MISS','FUN','FHOLD','FMISS','FERR','pure_SUP','has_UNSUP','mixed','branch']
main={cond:{key:dict(prior=pooled(pm,cond,key),current=pooled(cm,cond,key)) for key in KEYS} for cond in ('v5','B2')}
for cond in ('v5','B2'):
    for k in ('doubtful_parents','zero_doubt_outputs','any_UNSUP_outputs'):
        main[cond][k]=dict(prior=pm['pooled_alternative'][cond][k],current=cm['pooled_alternative'][cond][k])
gew={key:{lab:dict(prior=pm['group_equal_weight_overall'][key][lab]['mean'],current=cm['group_equal_weight_overall'][key][lab]['mean']) for lab in ('v5','B2','paired_difference')} for key in ('FUN','FERR','has_UNSUP')}
def row(m,q,cond):
    r=next(x for x in m['primary_rows'] if x['input_id']==q and x['condition']==cond)
    R=r['relations'];Pp=r['parents']
    return dict(RP=R['RP'],RF=R['RF'],DET=R['DET']['n'],HOLD=R['HOLD']['n'],FUN=R['FUN']['n'],FHOLD=R['FHOLD']['n'],FMISS=R['FMISS']['n'],FERR=R['FERR']['n'],
                parents=Pp['total'],doubtful=Pp['doubtful'],has_UNSUP=Pp['flags']['has_UNSUP']['n'],claims=Pp['claims_total'])
perq={q:{cond:dict(prior=row(pm,q,cond),current=row(cm,q,cond)) for cond in ('v5','B2')} for q in qs}
out=dict(kind='cross-run comparison of two LLM manual-rehearsal runs; neither run is ground truth',
  alignment_by='実行者（メイン、claude-opus-5-5）が封印解除後に audit-rules-v1 §2 の基準で作成。サブエージェントは使っていない。',
  reference=ref_cmp,audit_on_common_refs=audit_cmp,main_metrics_pooled=main,group_equal_weight=gew,per_input=perq)
(ROOT/'cross-run.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({k:ref_cmp[k] for k in ('n_current','n_prior','matched','dice','jaccard','polarity_agreement')},ensure_ascii=False))
print(audit_cmp['agreement']);[print(r) for r in rows if not r['same']]
for cond in ('v5','B2'): print(cond,{k:(f"{v['prior']['n']}/{v['prior']['den']}",f"{v['current']['n']}/{v['current']['den']}") if isinstance(v['prior'],dict) else (v['prior'],v['current']) for k,v in main[cond].items()})
print(json.dumps(gew))
for q in qs: print(q,{c:(perq[q][c]['prior'],perq[q][c]['current']) for c in ('v5','B2')})
