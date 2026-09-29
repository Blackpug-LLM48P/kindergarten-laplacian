"""Trial → Layer 1 特徴量（1 行 = 1 trial のフラットな dict）。"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Iterable

from .. import FEATURE_VERSION
from ..schema import Trial
from .code_audit import audit_code
from .formula import check_formula
from .metaphor import Lexicon, load_lexicon, metaphor_features
from .structure import structure_features
from .textspans import segment

ID_COLUMNS = ("trial_id", "model", "model_version", "version_source", "surface", "lang", "timestamp", "tokens_out")


def extract_features(trial: Trial, lexicon: Lexicon | None = None) -> dict[str, Any]:
    text = trial.response_text
    spans = segment(text)
    lex = lexicon or load_lexicon()

    met = metaphor_features(text, spans, lex)
    struct = structure_features(text, trial.lang, met.metaphor_offsets, spans)
    form = check_formula(text, spans)
    code = audit_code(trial.code_blocks or [], trial.exec_log)

    row: dict[str, Any] = {k: getattr(trial, k) for k in ID_COLUMNS}
    row["params"] = json.dumps(trial.params, ensure_ascii=False, sort_keys=True)
    row["feature_version"] = FEATURE_VERSION
    row["n_inferred_spans"] = sum(1 for s in spans if s.inferred)

    row.update({k: v for k, v in asdict(struct).items()})
    row["section_tags"] = json.dumps(struct.section_tags)

    row.update({
        "formula_status": form.status,
        "formula_present": form.status in ("correct", "incorrect", "unparseable"),
        "formula_position": form.position,
        "formula_first_pos": form.first_pos,
        "formula_last_pos": form.last_pos,
        "formula_n_candidates": form.n_candidates,
        "formula_n_unparseable": form.n_unparseable,
        "formula_any_incorrect": form.any_incorrect,
        "formula_final_expr": form.final_expr,
    })

    c = asdict(code)
    c["verification_types"] = json.dumps(code.verification_types)
    row.update(c)

    m = asdict(met)
    m.pop("metaphor_offsets")
    m["metaphor_categories"] = json.dumps(met.metaphor_categories)
    row.update(m)
    return row


def extract_all(trials: Iterable[Trial], lexicon: Lexicon | None = None) -> list[dict[str, Any]]:
    lex = lexicon or load_lexicon()
    return [extract_features(t, lex) for t in trials]
