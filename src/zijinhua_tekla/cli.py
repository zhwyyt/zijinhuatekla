import argparse
from pathlib import Path

from .part_drawing.pipeline import run_part_drawing_batch
from .pipeline.offline import run_offline_analysis
from .reports.offline import write_offline_analysis_report


def analyze(root, truth_root, member_id, assembly_id=None):
    result = run_offline_analysis(root, truth_root, member_id, assembly_id)
    return result.member, result.assembly, result.aligned_rows


def build_parser():
    parser = argparse.ArgumentParser(description="Analyze Zijinhua Tekla processing alignment.")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--root", required=True)
    analyze_parser.add_argument("--truth-root", required=True)
    analyze_parser.add_argument("--member-id", required=True)
    analyze_parser.add_argument("--assembly-id", default="")
    analyze_parser.add_argument("--out", default="outputs")
    draw_parts_parser = sub.add_parser("draw-parts")
    draw_parts_parser.add_argument("--snapshot-root", required=True)
    draw_parts_parser.add_argument("--out", default="outputs/part-drawings")
    draw_parts_parser.add_argument("--cjk-font", default="")
    return parser


def _run_draw_parts(args) -> int:
    result = run_part_drawing_batch(
        Path(args.snapshot_root),
        Path(args.out),
        Path(args.cjk_font) if args.cjk_font else None,
    )
    print(
        f"Part drawings: OK={result.ok_count} "
        f"REVIEW_REQUIRED={result.review_count} REJECTED={result.rejected_count}"
    )
    return 1 if result.rejected_count else 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "draw-parts":
        return _run_draw_parts(args)
    if args.command == "analyze":
        root = Path(args.root)
        truth_root = Path(args.truth_root)
        result = run_offline_analysis(root, truth_root, args.member_id, args.assembly_id or None)
        paths = write_offline_analysis_report(result, Path(args.out), args.member_id)
        print(f"Wrote {paths.csv_path}")
        print(f"Wrote {paths.json_path}")
        print(f"Wrote {paths.spatial_csv_path}")
        print(f"Wrote {paths.spatial_json_path}")
        print(f"Wrote {paths.quality_csv_path}")
        print(f"Wrote {paths.quality_json_path}")
        print(f"Wrote {paths.quality_review_tasks_path}")
        print(f"Wrote {paths.quality_review_tasks_csv_path}")
        print(f"Wrote {paths.quality_review_summary_path}")
        print(f"Wrote {paths.quality_review_summary_csv_path}")
        print(f"Wrote {paths.missing_candidates_path}")
        print(f"Wrote {paths.missing_candidates_csv_path}")
        print(f"Wrote {paths.conflict_candidates_path}")
        print(f"Wrote {paths.conflict_candidates_csv_path}")
        print(f"Wrote {paths.manufacturing_scope_path}")
        print(f"Wrote {paths.manufacturing_scope_csv_path}")
        print(f"Wrote {paths.box_main_material_segments_path}")
        print(f"Wrote {paths.box_main_material_segments_csv_path}")
        print(f"Wrote {paths.box_part_spatial_relations_path}")
        print(f"Wrote {paths.box_part_spatial_relations_csv_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_csv_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_md_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_dxf_path}")
        print(f"Wrote {paths.box_station_topology_diagnostics_path}")
        print(f"Wrote {paths.box_station_topology_diagnostics_csv_path}")
        print(f"Wrote {paths.markdown_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

