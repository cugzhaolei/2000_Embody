"""
具身数据集格式转换 CLI
=====================
支持 LeRobot / ROS Bag / MCAP 格式之间的相互转换。
"""

import argparse
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def convert_to_lerobot(args):
    """转换为 LeRobot 格式"""
    from conversion.lerobot_converter import LeRobotConverter

    input_path = Path(args.input)
    output_dir = args.output or str(input_path.parent / "lerobot_output")

    converter = LeRobotConverter(output_dir)

    if input_path.is_dir():
        # 假设是内部格式的 episode 目录
        import json
        episodes = []
        for ep_file in sorted(input_path.glob("*.json")):
            with open(ep_file) as f:
                episodes.append(json.load(f))
    else:
        print(f"Error: {input_path} is not a directory")
        return

    result_path = converter.from_internal_dataset(
        episodes,
        dataset_name=args.dataset_name or "converted_dataset",
        robot_type=args.robot_type or "so101",
        fps=args.fps or 30.0,
    )
    print(f"Converted to LeRobot: {result_path}")


def convert_from_lerobot(args):
    """从 LeRobot 格式转换"""
    from conversion.lerobot_converter import LeRobotConverter

    input_path = args.input
    output_dir = args.output or str(Path(input_path).parent / "internal_output")

    converter = LeRobotConverter(output_dir)
    episodes = converter.to_internal_dataset(input_path)

    import json
    output_path = Path(output_dir) / "converted_episodes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(episodes, f, indent=2, default=str)

    print(f"Converted {len(episodes)} episodes from LeRobot: {output_path}")


def convert_from_rosbag(args):
    """从 ROS Bag 转换"""
    from conversion.rosbag_converter import ROSBagConverter

    output_dir = args.output or "./converted_data"
    converter = ROSBagConverter(output_dir)

    bag_data = converter.read_ros2_bag(args.input)
    internal_data = converter.convert_to_internal(bag_data)

    import json
    output_path = Path(output_dir) / "rosbag_converted.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {k: {kk: vv.tolist() if hasattr(vv, 'tolist') else vv for kk, vv in v.items()}
             if isinstance(v, dict) else v
             for k, v in internal_data.items()},
            f, indent=2, default=str
        )

    print(f"Converted from ROS Bag: {output_path}")


def inspect_dataset(args):
    """检查数据集信息"""
    input_path = Path(args.input)

    if input_path.suffix == ".parquet":
        import pandas as pd
        df = pd.read_parquet(str(input_path))
        print(f"Parquet file: {input_path}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Size: {input_path.stat().st_size / 1024:.1f} KB")

    elif input_path.suffix in (".h5", ".hdf5"):
        from storage.hdf5_store import HDF5Store
        store = HDF5Store(str(input_path))
        store.open("r")
        stats = store.get_stats()
        store.close()
        print(f"HDF5 file: {input_path}")
        print(f"  Episodes: {stats['num_episodes']}")
        print(f"  Size: {stats['total_size_mb']:.1f} MB")

    elif input_path.is_dir():
        # 检查目录结构
        files = list(input_path.rglob("*"))
        parquet_files = [f for f in files if f.suffix == ".parquet"]
        print(f"Dataset directory: {input_path}")
        print(f"  Total files: {len(files)}")
        print(f"  Parquet files: {len(parquet_files)}")


def main():
    parser = argparse.ArgumentParser(description="具身数据集格式转换工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # convert-to-lerobot
    p1 = subparsers.add_parser("to-lerobot", help="转换为 LeRobot 格式")
    p1.add_argument("input", help="输入目录")
    p1.add_argument("-o", "--output", help="输出目录")
    p1.add_argument("--dataset-name", help="数据集名称")
    p1.add_argument("--robot-type", default="so101", help="机器人类型")
    p1.add_argument("--fps", type=float, default=30.0, help="帧率")

    # convert-from-lerobot
    p2 = subparsers.add_parser("from-lerobot", help="从 LeRobot 格式转换")
    p2.add_argument("input", help="LeRobot 数据集目录")
    p2.add_argument("-o", "--output", help="输出目录")

    # convert-from-rosbag
    p3 = subparsers.add_parser("from-rosbag", help="从 ROS Bag 转换")
    p3.add_argument("input", help="ROS Bag 路径")
    p3.add_argument("-o", "--output", help="输出目录")

    # inspect
    p4 = subparsers.add_parser("inspect", help="检查数据集信息")
    p4.add_argument("input", help="数据集路径")

    args = parser.parse_args()

    if args.command == "to-lerobot":
        convert_to_lerobot(args)
    elif args.command == "from-lerobot":
        convert_from_lerobot(args)
    elif args.command == "from-rosbag":
        convert_from_rosbag(args)
    elif args.command == "inspect":
        inspect_dataset(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
