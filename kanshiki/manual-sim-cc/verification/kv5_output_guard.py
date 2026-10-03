"""Output-level structural checks, not semantic validation of findings."""
import re
from decimal import Decimal,InvalidOperation
from kv5common import ALL_IDS,FACE_TOTAL

NUMBER=r'[+\-−－＋﹣﹢–—]?\d+(?:\.\d+)*'
SCORE=re.compile(r'(?<![\w.])('+NUMBER+r')\s*[/／]\s*100(?![\d.])')
RATE=re.compile(r'評価済み率[^\d\n+\-−－＋﹣﹢–—]{0,20}?('+NUMBER+r')\s*[%％]')
WIDTH=re.compile(r'欠測幅[^\d\n+\-−－＋﹣﹢–—]{0,30}?('+NUMBER+r')\s*[%％]?\s*[〜~～\-–—]\s*('+NUMBER+r')\s*[%％]?')
FRAC=re.compile(r'(?<![\w.])([+\-−－＋﹣﹢–—]?\d+)\s*[/／]\s*([+\-−－＋﹣﹢–—]?\d+)(?![\d.])')
# Include malformed and unknown ID-shaped rows so a valid 29-row subset is insufficient.
CANDIDATE=re.compile(r'^\s*(?:[|｜]\s*|[-*・]\s*)?\**([A-Z]\d{2,})\**[^|｜:：\n]{0,40}?[|｜:：]')


def row_candidates(nofence,matcher):
    candidates=[]
    for n,line in enumerate(nofence.split('\n'),1):
        m=CANDIDATE.match(line)
        if not m:continue
        if m.group(1)[0] not in 'SCRE' and not line.lstrip().startswith(('|','｜')):continue
        valid=matcher.match(line)
        candidates.append(dict(line=n,id=m.group(1),valid=bool(valid),reason='unknown ID' if m.group(1) not in ALL_IDS else 'invalid category/row' if not valid else ''))
    return candidates


def select_ledger(blocks,candidates,index=None):
    complete=[b for b in blocks if b['complete']]
    if index is None:
        if not complete:return None,'fail','29ID台帳を特定できない'
        if len(complete)!=1:return None,'unverifiable','複数の完全な台帳がある。現在値の台帳を番号で指定する必要がある'
        chosen=complete[0]
        if any(not c['valid'] or c['id'] not in ALL_IDS for c in candidates):return chosen,'fail','不正または未知IDの台帳行がある'
        if len(candidates)!=29:return chosen,'fail','保存用台帳以外にもID区分行がある。複数範囲は明示選択が必要'
    else:
        if isinstance(index,bool) or not isinstance(index,int) or index<1 or index>len(complete):return None,'unverifiable','台帳番号が範囲外'
        chosen=complete[index-1]
        # Scope is the ID-row cluster, not arbitrary nearby prose or other explicit versions.
        lo,hi=chosen['rows'][0]['line'],chosen['rows'][-1]['line']
        relevant=[c for c in candidates if lo<=c['line']<=hi]
        if len(relevant)!=29 or any(not c['valid'] or c['id'] not in ALL_IDS for c in relevant):return chosen,'fail','選択した台帳に不正・余分なID行がある'
    return chosen,'pass','明示選択' if index is not None else '一意の完全台帳'


def score_sections(nofence):
    lines=nofence.split('\n');starts=[n for n,line in enumerate(lines) if '文章疑義スコア' in line]
    return ['\n'.join(lines[start:min(start+20,starts[n+1] if n+1<len(starts) else len(lines))]) for n,start in enumerate(starts)]


def numbers(exp,section):
    problems=[];out={'expected':{k:exp[k] for k in ('state','score','score_fraction','rate','width')}}
    if not section:return dict(out,status='unverifiable',reason='「文章疑義スコア」の欄が見つからない')
    rate_at=section.find('評価済み率');width_at=section.find('欠測幅');score_part=section[:rate_at] if rate_at>=0 else section
    rate_part=section[rate_at:width_at] if rate_at>=0 and width_at>rate_at else section[rate_at:] if rate_at>=0 else ''
    width_part=section[width_at:] if width_at>=0 else ''
    # Only the numeric subsection before the four-face table, not unrelated prose.
    for marker in ('\n面｜','\n| 面','\nS 文体','\n■ '):
        score_part=score_part.split(marker,1)[0];rate_part=rate_part.split(marker,1)[0];width_part=width_part.split(marker,1)[0]
    scores=list(SCORE.finditer(score_part));rates=list(RATE.finditer(rate_part));widths=list(WIDTH.finditer(width_part))
    state_labels=re.findall(r'^\s*(?:[-*] ?)?(?:スコア[：:]\s*)?(算出不可|未検算)',score_part,flags=re.M)
    out['shown_state']=state_labels[0] if state_labels else '数値'
    if len(scores)>1:problems.append('スコアの数値が複数ある')
    if len(rates)>1:problems.append('評価済み率の数値が複数ある')
    if len(widths)>1:problems.append('欠測幅の数値が複数ある')
    def decimal_value(value,expected,label):
        if not re.fullmatch(r'\d{1,3}\.\d',value):problems.append(label+'の表示桁が小数第1位でない: '+value)
        try:
            v=Decimal(value)
            if not 0<=v<=100:problems.append(label+'が0〜100の範囲外')
            if v!=Decimal(expected):problems.append(label+'不一致: 表示'+value+' / 再計算'+expected)
        except InvalidOperation:problems.append(label+'の数値表記が不正: '+value)
    def fraction_check(part,expected,label):
        # Score /100 is a display denominator, not the exact P/K fraction.
        shown=[]
        for m in FRAC.finditer(part):
            if label=='スコア' and m.group(2)=='100':continue
            if not all(re.fullmatch(r'\d+',v) for v in m.groups()):
                problems.append(label+'の分数の符号・表記が不正: '+m.group(0));continue
            shown.append((int(m.group(1)),int(m.group(2))))
        if shown!=expected:problems.append(label+'の正確な分数が欠落・不一致・重複: '+str(shown)+' / '+str(expected))
    if exp['state']=='算出不可':
        if not state_labels or state_labels[0]!='算出不可':problems.append('ΣK=0なのに算出不可と表示していない')
        if scores:problems.append('算出不可なのに数値スコアを表示している')
    else:
        if state_labels:problems.append('検算可能なスコアに算出不可／未検算を併記している')
        if len(scores)!=1:problems.append('スコアの数値を一意に特定できない')
        else:out['shown_score']=scores[0].group(1);decimal_value(out['shown_score'],exp['score'],'スコア')
        fraction_check(score_part,[(exp['total']['P'],exp['total']['K'])],'スコア')
    n=29-exp['total']['X']
    if exp['rate'] is None:
        if rates:problems.append('適用項目0なのに評価済み率の数値を表示している')
        if not re.search(r'評価済み率[^\n。]{0,20}算出不可',section):problems.append('適用項目0の評価済み率を算出不可と表示していない')
    else:
        if len(rates)!=1:problems.append('評価済み率が見つからない／一意でない（29−ΣX>0では必須）')
        else:out['shown_rate']=rates[0].group(1);decimal_value(out['shown_rate'],exp['rate'],'評価済み率')
        fraction_check(rate_part,[(exp['total']['K'],n)],'評価済み率')
    if exp['width'] is None:
        if widths:problems.append('ΣU=0または適用項目0なのに数値の欠測幅がある')
        if n==0 and not re.search(r'欠測幅[^\n。]{0,20}算出不可',section):problems.append('適用項目0の欠測幅を算出不可と表示していない')
    else:
        if len(widths)!=1:problems.append('欠測幅が見つからない／一意でない（ΣU>0では必須）')
        else:
            values=[widths[0].group(1),widths[0].group(2)];out['shown_width']=values
            for value,expected in zip(values,exp['width']):decimal_value(value,expected,'欠測幅')
        fraction_check(width_part,[(exp['total']['P'],n),(exp['total']['P']+exp['total']['U'],n)],'欠測幅')
    out['problems']=problems;out['status']='fail' if problems else 'pass';return out

FACE_CANDIDATE=re.compile(r'^\s*[|｜]?\s*\**([A-Z])\**\s*[^|｜\d\n]{0,10}[|｜]\s*[^\n]*[/／][^\n]*[/／][^\n]*[/／]')
def invalid_face_rows(nofence,matcher):
    result=[]
    for n,line in enumerate(nofence.split('\n'),1):
        candidate=FACE_CANDIDATE.match(line)
        if candidate and not matcher.match(line):result.append(dict(line=n,face=candidate.group(1),head=line[:120]))
    return result
