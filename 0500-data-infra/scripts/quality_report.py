"""
数据集质量报告生成器
===================
对数据集进行全面质量检查并输出报告。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def generate_quality_report(args):
    """生成数据集质量报告"""
    from quality.image_quality import ImageQualityChecker
    from quality.trajectory_check import TrajectoryChecker
    from quality.sync_check import SyncChecker
    import numpy as np

    input_path = Path(args.input)

    print(f"=== 具身数据集质量报告 ===")
    print(f"数据集路径: {input_path}\n")

    report = {
        "dataset_path": str(input_path),
        "episodes": {},
        "summary": {},
    }

    # 加载数据
    if input_path.is_dir():
        ep_files = sorted(input_path.glob("*.json"))
        print(f"发现 {len(ep_files)} 个 Episode 文件\n")

        img_checker = ImageQualityChecker()
        traj_checker = TrajectoryChecker()
        sync_checker = SyncChecker()

        total_score = 0
        total_episodes = 0

        for ep_file in ep_files:
            with open(ep_file) as f:
                ep_data = json.load(f)

            ep_id = ep_file.stem
            ep_report = {"issues": []}

            # 图像质量检查
            if "rgb" in ep_data:
                rgb = np.array(ep_data["rgb"])
                if rgb.ndim >= 3:
                    img_report = img_checker.check_sequence(rgb, sample_rate=5)
                    ep_report["image_quality"] = {
                        "score": img_report.overall_score,
                        "issues": len(img_report.issues),
                    }
                    if img_report.issues:
                        ep_report["issues"].extend(img_report.issues[:3])

            # 轨迹检查
            if "eef_pose" in ep_data:
                pose = np.array(ep_data["eef_pose"])
                if pose.ndim == 2:
                    traj_result = traj_checker.check(pose)
                    ep_report["trajectory"] = {
                        "smoothness": traj_result.smoothness_score,
                        "jumps": traj_result.jump_count,
                        "success": traj_result.success,
                    }
                    if traj_result.issues:
                        ep_report["issues"].extend(traj_result.issues[:3])

            # 动作检查
            if "action" in ep_data:
                action = np.array(ep_data["action"])
                ep_report["action_stats"] = {
                    "mean": float(np.abs(action).mean()) if action.size > 0 else 0,
                    "max": float(np.abs(action).max()) if action.size > 0 else 0,
                    "has_nan": bool(np.isnan(action).any()) if hasattr(action, 'any') else False,
                }

            report["episodes"][ep_id] = ep_report
            total_episodes += 1

        # 汇总
        if total_episodes > 0:
            scores = [
                ep.get("image_quality", {}).get("score", 0.5)
                for ep in report["episodes"].values()
            ]
            report["summary"] = {
                "total_episodes": total_episodes,
                "avg_quality_score": round(np.mean(scores), 3) if scores else 0,
                "episodes_with_issues": sum(
                    1 for ep in report["episodes"].values() if ep.get("issues")
                ),
            }

    # 输出报告
    print("--- Episode 质量摘要 ---")
    for ep_id, ep_report in list(report["episodes"].items())[:10]:
        score = ep_report.get("image_quality", {}).get("score", "N/A")
        issues = len(ep_report.get("issues", []))
        print(f"  {ep_id}: score={score}, issues={issues}")

    print(f"\n--- 总结 ---")
    summary = report.get("summary", {})
    print(f"  总 Episode 数: {summary.get('total_episodes', 0)}")
    print(f"  平均质量分: {summary.get('avg_quality_score', 0)}")
    print(f"  有问题的 Episode: {summary.get('episodes_with_issues', 0)}")

    # 保存报告
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path / "quality_report.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n报告已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="数据集质量报告生成器")
    parser.add_argument("input", help="数据集目录路径")
    parser.add_argument("-o", "--output", help="报告输出路径")

    args = parser.parse_args()
    generate_quality_report(args)


if __name__ == "__main__":
    main()
