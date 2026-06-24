import argparse
from pathlib import Path

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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
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
        print(f"Wrote {paths.markdown_path}")


if __name__ == "__main__":
    main()

