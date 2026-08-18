"""
坐标变换模块
===========
机器人多坐标系变换、TF 链管理、相机-机器人标定变换。
"""

from typing import Dict, List, Optional, Tuple

import numpy as np


class CoordinateTransformer:
    """坐标变换管理器

    管理机器人系统中的多坐标系变换关系，支持:
    - 齐次变换矩阵
    - 欧拉角/四元数互转
    - 多级 TF 链变换
    - 相机-机器人手眼标定
    """

    def __init__(self):
        self._transforms: Dict[Tuple[str, str], np.ndarray] = {}

    def set_transform(
        self,
        parent_frame: str,
        child_frame: str,
        transform: np.ndarray,
    ) -> None:
        """设置两个坐标系之间的变换"""
        self._transforms[(parent_frame, child_frame)] = transform

    def get_transform(
        self,
        from_frame: str,
        to_frame: str,
    ) -> Optional[np.ndarray]:
        """查找 from_frame -> to_frame 的变换"""
        # 直接查找
        direct = self._transforms.get((from_frame, to_frame))
        if direct is not None:
            return direct

        # 反向查找
        inverse = self._transforms.get((to_frame, from_frame))
        if inverse is not None:
            return self.invert_transform(inverse)

        # BFS 查找路径
        path = self._find_path(from_frame, to_frame)
        if path is None:
            return None

        result = np.eye(4)
        for i in range(len(path) - 1):
            t = self._transforms.get((path[i], path[i + 1]))
            if t is None:
                t_inv = self._transforms.get((path[i + 1], path[i]))
                if t_inv is not None:
                    t = self.invert_transform(t_inv)
                else:
                    return None
            result = result @ t
        return result

    def _find_path(self, start: str, end: str) -> Optional[List[str]]:
        """BFS 搜索坐标系路径"""
        from collections import deque

        visited = {start}
        queue = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            if current == end:
                return path

            for (parent, child) in self._transforms:
                neighbor = child if parent == current else (parent if child == current else None)
                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    @staticmethod
    def make_transform(
        translation: Tuple[float, float, float] = (0, 0, 0),
        rotation_euler: Tuple[float, float, float] = (0, 0, 0),
    ) -> np.ndarray:
        """从平移和欧拉角创建齐次变换矩阵"""
        x, y, z = translation
        rx, ry, rz = rotation_euler

        # 旋转矩阵 (ZYX 欧拉角)
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)],
        ])
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)],
        ])
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1],
        ])
        R = Rz @ Ry @ Rx

        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    @staticmethod
    def make_transform_quaternion(
        translation: Tuple[float, float, float],
        quaternion: Tuple[float, float, float, float],
    ) -> np.ndarray:
        """从平移和四元数创建齐次变换矩阵"""
        x, y, z = translation
        qx, qy, qz, qw = quaternion

        # 四元数转旋转矩阵
        R = np.array([
            [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qz*qw), 2*(qx*qz + qy*qw)],
            [2*(qx*qy + qz*qw), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qx*qw)],
            [2*(qx*qz - qy*qw), 2*(qy*qz + qx*qw), 1 - 2*(qx**2 + qy**2)],
        ])

        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    @staticmethod
    def invert_transform(T: np.ndarray) -> np.ndarray:
        """求逆变换"""
        R = T[:3, :3]
        t = T[:3, 3]
        T_inv = np.eye(4)
        T_inv[:3, :3] = R.T
        T_inv[:3, 3] = -R.T @ t
        return T_inv

    @staticmethod
    def decompose_transform(T: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """分解变换矩阵为 (translation, rotation_matrix, euler_angles)"""
        translation = T[:3, 3]
        R = T[:3, :3]

        # 欧拉角 (ZYX)
        ry = np.arctan2(-R[2, 0], np.sqrt(R[0, 0]**2 + R[1, 0]**2))
        rx = np.arctan2(R[2, 1], R[2, 2])
        rz = np.arctan2(R[1, 0], R[0, 0])
        euler = np.array([rx, ry, rz])

        return translation, R, euler

    def transform_point(
        self, point: np.ndarray, from_frame: str, to_frame: str
    ) -> Optional[np.ndarray]:
        """变换点坐标"""
        T = self.get_transform(from_frame, to_frame)
        if T is None:
            return None

        if point.ndim == 1:
            point_h = np.append(point, 1.0)
        else:
            point_h = np.hstack([point, np.ones((len(point), 1))])

        transformed = (T @ point_h.T).T
        return transformed[:, :3] if transformed.shape[1] > 3 else transformed[:3]

    @staticmethod
    def camera_to_robot_transform(
        camera_intrinsics: Dict[str, float],
        extrinsics: np.ndarray,
        pixel: Tuple[int, int],
        depth: float,
    ) -> np.ndarray:
        """相机像素坐标 -> 机器人基坐标系 3D 点"""
        fx = camera_intrinsics["fx"]
        fy = camera_intrinsics["fy"]
        cx = camera_intrinsics["cx"]
        cy = camera_intrinsics["cy"]

        u, v = pixel
        x_cam = (u - cx) * depth / fx
        y_cam = (v - cy) * depth / fy
        z_cam = depth

        point_camera = np.array([x_cam, y_cam, z_cam, 1.0])
        point_robot = extrinsics @ point_camera
        return point_robot[:3]
