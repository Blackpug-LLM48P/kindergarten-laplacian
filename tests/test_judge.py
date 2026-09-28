from bench29.judge.calibrate import score
from bench29.judge.run_judge import BINARY_AXES, OUTPUT_SCHEMA, judge_trial, rubric_version
from bench29.schema import Trial

TEXT = "ピザで考えよう。外側ほど一切れが広い。連鎖律を2回使って整理すると、答えが出ます。"


class FakeJudge:
    model = "fake-judge-1"

    def __init__(self, escape=True):
        self.escape = escape

    def judge(self, system, prompt, schema):
        assert schema is OUTPUT_SCHEMA and "rubric_version" in system
        out = {axis: {"present": False, "evidence": []} for axis in BINARY_AXES}
        out["rhetorical_derivation_escape"] = {
            "present": self.escape,
            "evidence": ["連鎖律を2回使って整理すると", "本文にない引用"] if self.escape else [],
        }
        out.update({"stretch_level": 1, "stretch_evidence": ["外側ほど一切れが広い"]})
        return out, "fake-judge-1-20260928"


def _trial(i=0):
    return Trial(f"t{i}", "m", "v1", "chat", "ja", TEXT)


def test_judge_records_versions_and_verifies_spans():
    row = judge_trial(_trial(), FakeJudge())
    assert row["judge_model"] == "fake-judge-1"
    assert row["judge_version"] == "fake-judge-1-20260928"
    assert row["rubric_version"] == rubric_version() and "msf-" in row["rubric_version"]
    assert row["rhetorical_derivation_escape_evidence"] == ["連鎖律を2回使って整理すると"]
    assert row["evidence_unverified"] == {"rhetorical_derivation_escape": ["本文にない引用"]}
    assert row["metaphor_drift"] == row["drift"]


def test_calibration_accepts_and_rejects():
    anchors = [{"trial": _trial(i), "labels": {"kp": {"stretch_level": 1, "rhetorical_derivation_escape": i % 2 == 0,
                                                      **{a: False for a in BINARY_AXES if a != "rhetorical_derivation_escape"}}}}
               for i in range(6)]
    good = {f"t{i}": {"stretch_level": 1, "rhetorical_derivation_escape": i % 2 == 0,
                      **{a: False for a in BINARY_AXES if a != "rhetorical_derivation_escape"}} for i in range(6)}
    assert score(anchors, good)["accepted"]
    bad = {k: {**v, "rhetorical_derivation_escape": not v["rhetorical_derivation_escape"]} for k, v in good.items()}
    res = score(anchors, bad)
    assert not res["accepted"] and res["axes"]["rhetorical_derivation_escape"]["kappa"] < 0
