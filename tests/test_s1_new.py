"""S1 新增 contracts/adapters/cases 模块测试."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from zijinhua_tekla.contracts.member import MemberType, MemberBodyType, MemberRecord
from zijinhua_tekla.contracts.part import PartRecord, PartFeatureSnapshot
from zijinhua_tekla.contracts.assembly import AssemblyRecord, Relationship, RelationshipType
from zijinhua_tekla.contracts.role import PartRole, Evidence, PartRoleResult
from zijinhua_tekla.contracts.process import ProcessType, ProcessRoute
from zijinhua_tekla.contracts.sequence import AssemblyStep, DimensionAnnotation

from zijinhua_tekla.adapters.tekla_bundle import adapt_assembly
from zijinhua_tekla.adapters.teklatest_features import adapt_snapshot
from zijinhua_tekla.adapters.bundle_export import assembly_to_dict

from zijinhua_tekla.cases.bank import CaseBank, CaseFeedback, CaseIssueType
from zijinhua_tekla.cases.feedback import suggest_attribution, REASON_TARGETS
from zijinhua_tekla.config import AnalysisContext, ColumnMapping


# ── contracts ──

class TestMemberContract:
    def test_member_type_values(self):
        assert MemberType.COL == "COL"
        assert MemberType.BEAM == "BEAM"
        assert MemberType.UNKNOWN == "UNKNOWN"

    def test_member_body_values(self):
        assert MemberBodyType.BOX == "BOX"
        assert MemberBodyType.H_I == "H_I"
        assert MemberBodyType.CROSS == "CROSS"

    def test_member_record_frozen(self):
        r = MemberRecord(
            member_id="M1", assembly_id="A1",
            member_type=MemberType.COL, body_type=MemberBodyType.BOX,
            body_confidence=0.95, body_evidence=["test"],
            main_part_ids=["P1"], total_parts=5, total_relationships=8,
        )
        assert r.member_id == "M1"
        assert r.total_parts == 5


class TestPartContract:
    def test_part_record_defaults(self):
        p = PartRecord(part_id="P1")
        assert p.position == ""
        assert p.thickness == 0.0

    def test_feature_snapshot_fields(self):
        snap = PartFeatureSnapshot(
            part_id="P2", hole_like_feature_count=3,
            obb_dims={"x": 100.0, "y": 200.0, "z": 10.0},
        )
        assert snap.hole_like_feature_count == 3
        assert snap.obb_dims["x"] == 100.0


class TestAssemblyContract:
    def test_assembly_record(self):
        rel = Relationship("A", "B", RelationshipType.WELD, ["test"])
        rec = AssemblyRecord(
            assembly_id="ASM1", main_part_id="A",
            part_ids=["A", "B"], relationships=[rel],
        )
        assert len(rec.relationships) == 1
        assert rec.relationships[0].edge_type == RelationshipType.WELD


class TestRoleContract:
    def test_part_role_enum(self):
        assert PartRole.FLANGE == "FLANGE"
        assert PartRole.DIAPHRAGM == "DIAPHRAGM"
        assert PartRole.UNKNOWN == "UNKNOWN"

    def test_evidence(self):
        e = Evidence(code="THICK", description="厚度匹配", weight=1.5)
        assert e.weight == 1.5


class TestProcessContract:
    def test_process_type(self):
        assert ProcessType.LASER_CUT == "LASER_CUT"
        assert ProcessType.BENDING == "BENDING"

    def test_process_route(self):
        route = ProcessRoute(
            part_id="P1", processes=[ProcessType.LASER_CUT, ProcessType.DRILLING],
            confidence=0.9, evidence=["ok"],
        )
        assert len(route.processes) == 2


class TestSequenceContract:
    def test_assembly_step(self):
        dim = DimensionAnnotation(label="长度", value_mm=1200.0, annotation_type="length")
        step = AssemblyStep(
            step_number=1, description="放置主材", part_ids=["P1"],
            action="place", dimensions=[dim], confidence=1.0, evidence=["test"],
        )
        assert step.step_number == 1
        assert step.dimensions[0].value_mm == 1200.0


# ── adapters ──

class TestTeklaBundleAdapter:
    def test_adapt_assembly(self):
        raw = {
            "assemblyId": "ASM1",
            "mainPartId": "P1",
            "parts": [
                {"partId": "P1", "partPosition": "B-1", "partName": "腹板",
                 "profile": "PL20*400", "thickness": 20, "length": 400},
                {"partId": "P2", "partPosition": "B-2", "partName": "翼缘板",
                 "profile": "PL20*400", "thickness": 20},
            ],
            "relationships": [
                {"partIdA": "P1", "partIdB": "P2", "edgeType": "Weld"},
            ],
        }
        asm, parts = adapt_assembly(raw)
        assert asm.assembly_id == "ASM1"
        assert asm.main_part_id == "P1"
        assert len(parts) == 2
        assert parts[0].part_id == "P1"
        assert len(asm.relationships) == 1


class TestTeklatestAdapter:
    def test_adapt_snapshot(self):
        raw = {
            "partId": "P1", "partPosition": "B-1", "thickness": 12,
            "holeLikeFeatureCount": 5, "obb": {"x": 100, "y": 200, "z": 12},
        }
        snap = adapt_snapshot(raw)
        assert snap.part_id == "P1"
        assert snap.thickness == 12.0
        assert snap.hole_like_feature_count == 5
        assert snap.obb_dims["x"] == 100.0


class TestBundleExport:
    def test_assembly_to_dict(self):
        rel = Relationship("A", "B", RelationshipType.BOLT, ["ok"])
        asm = AssemblyRecord(assembly_id="X", part_ids=["A", "B"], relationships=[rel])
        d = assembly_to_dict(asm)
        assert d["assemblyId"] == "X"
        assert d["relationships"][0]["edgeType"] == "Bolt"


# ── cases ──

class TestCaseBank:
    def test_add_and_get(self):
        bank = CaseBank()
        fb = CaseFeedback(
            case_id="M1:P1", issue_type=CaseIssueType.DATA,
            expected_label="翼缘板", human_note="缺件",
            evidence_fields=["partId"],
        )
        bank.add(fb)
        assert bank.get("M1:P1") is not None
        assert len(bank.all()) == 1

    def test_by_issue_type(self):
        bank = CaseBank()
        bank.add(CaseFeedback(
            case_id="M1:P1", issue_type=CaseIssueType.DATA,
            expected_label="翼缘板", human_note="缺件", evidence_fields=["partId"],
        ))
        bank.add(CaseFeedback(
            case_id="M1:P2", issue_type=CaseIssueType.FEATURE,
            expected_label="腹板", human_note="特征不足", evidence_fields=["thickness"],
        ))
        assert len(bank.by_issue_type(CaseIssueType.DATA)) == 1
        assert len(bank.by_issue_type(CaseIssueType.FEATURE)) == 1

    def test_save_load_json(self):
        import tempfile
        bank = CaseBank()
        bank.add(CaseFeedback(
            case_id="M1:P1", issue_type=CaseIssueType.SCORING,
            expected_label="加劲板", human_note="权重不对",
            evidence_fields=["confidence"],
        ))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test_cases.json"
            bank.save_json(p)
            loaded = CaseBank.load_json(p)
            assert len(loaded.all()) == 1
            assert loaded.get("M1:P1").expected_label == "加劲板"

    def test_empty_seed_load(self):
        seed = Path(__file__).parent.parent / "src" / "zijinhua_tekla" / "cases" / "seed.json"
        if seed.exists():
            bank = CaseBank.load_json(seed)
            assert len(bank.all()) == 0


class TestCaseFeedback:
    def test_suggest_attribution(self):
        fb = CaseFeedback(
            case_id="M1:P1", issue_type=CaseIssueType.FEATURE,
            expected_label="腹板", human_note="缺少孔特征",
            evidence_fields=["hole_like_feature_count"],
        )
        result = suggest_attribution(fb)
        assert result.issue_type == CaseIssueType.FEATURE
        assert "Feature Snapshot" in result.suggestion

    def test_all_issue_types_have_targets(self):
        for it in CaseIssueType:
            assert it in REASON_TARGETS


# ── config ──

class TestConfig:
    def test_analysis_context_defaults(self):
        ctx = AnalysisContext()
        assert ctx.member_id == ""
        assert ctx.column_mapping.part_position == "零件名称"

    def test_column_mapping_custom(self):
        cm = ColumnMapping(part_position="编号", spec="型号")
        assert cm.part_position == "编号"
        assert cm.spec == "型号"