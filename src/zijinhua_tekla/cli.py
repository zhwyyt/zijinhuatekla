import argparse
from pathlib import Path

from .pipeline.offline import run_model_recognition, run_offline_analysis
from .reports.offline import write_offline_analysis_report
from .reports.recognition import write_recognition_workbook


def analyze(root, truth_root, member_id, assembly_id=None):
    result = run_offline_analysis(root, truth_root, member_id, assembly_id)
    return result.member, result.assembly, result.aligned_rows


def build_parser():
    parser = argparse.ArgumentParser(description="Zijinhua Tekla model recognition.")
    sub = parser.add_subparsers(dest="command", required=True)

    emit_parser = sub.add_parser("emit-excel", help="Model -> recognition Excel. No factory workbook.")
    _add_model_args(emit_parser)

    compare_parser = sub.add_parser("compare", help="Recognition vs factory workbook. Does not change labels.")
    _add_model_args(compare_parser)
    compare_parser.add_argument("--truth-root", required=True)

    analyze_parser = sub.add_parser("analyze", help="Emit plus optional compare. Default does not write DXF.")
    _add_model_args(analyze_parser)
    analyze_parser.add_argument("--truth-root", default="")
    analyze_parser.add_argument("--draw", action="store_true", help="Also write BOX drawing steps DXF.")
    sub.add_parser("gui", help="Open the combined Tekla export Excel GUI.")
    return parser


def _add_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True)
    parser.add_argument("--member-id", required=True)
    parser.add_argument("--assembly-id", default="")
    parser.add_argument("--out", default="outputs")


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "gui":
        from .gui.report_gui import main as run_gui

        run_gui()
        return

    root = Path(args.root)
    out_dir = Path(args.out)
    assembly_id = args.assembly_id or None
    include_drawings = bool(getattr(args, "draw", False))

    if args.command == "emit-excel":
        result = run_model_recognition(root, args.member_id, assembly_id, include_drawings=False)
        paths = write_recognition_workbook(result, out_dir, args.member_id)
        print(f"Wrote {paths.xlsx_path}")
        print(f"Wrote {paths.json_path}")
        return

    truth_root = Path(args.truth_root) if getattr(args, "truth_root", "") else None
    result = run_offline_analysis(
        root,
        truth_root,
        args.member_id,
        assembly_id,
        include_drawings=include_drawings,
    )
    recognition_paths = write_recognition_workbook(result, out_dir, args.member_id)
    print(f"Wrote {recognition_paths.xlsx_path}")
    print(f"Wrote {recognition_paths.json_path}")
    if truth_root is None:
        return
    paths = write_offline_analysis_report(result, out_dir, args.member_id, include_drawings=include_drawings)
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
    if include_drawings:
        print(f"Wrote {paths.box_assembly_drawing_steps_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_csv_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_md_path}")
        print(f"Wrote {paths.box_assembly_drawing_steps_dxf_path}")
    print(f"Wrote {paths.box_station_topology_diagnostics_path}")
    print(f"Wrote {paths.box_station_topology_diagnostics_csv_path}")
    print(f"Wrote {paths.markdown_path}")


if __name__ == "__main__":
    main()
