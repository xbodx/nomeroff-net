import os
import cv2
import sys
import numpy as np
from typing import List, Dict, Tuple

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from tools import (fline,
                   distance,
                   minimum_bounding_rectangle,
                   fixClockwise2,
                   linearLineMatrix,
                   getYByMatrix,
                   rotate,
                   detectIntersection,
                   findMinXIdx,
                   reshapePoints)
from BBoxNpMultiline import MultilineConverter


def normalize_multiline_rect(rect: np.ndarray, mline_boxes: List) -> np.ndarray:
    """
    TODO: describe function
    """
    rect = fixClockwise2(rect)
    min_x_idx = findMinXIdx(rect)
    rect = reshapePoints(rect, min_x_idx)

    w_max, w_max_idx, options = make_mline_boxes_options(mline_boxes)
    target_angle = options[w_max_idx]['angle']
    coef_ccw = fline(rect[0], rect[3])
    angle_ccw = round(coef_ccw[2], 2)

    if abs(target_angle-angle_ccw) > 45:
        rect = reshapePoints(rect, 3)
    return rect


def fix_box_angle(target_angle: float, mline_box: List, option: Dict) -> List:
    line_matrix_left = linearLineMatrix(mline_box[0], mline_box[2])
    line_matrix_right = linearLineMatrix(mline_box[1], mline_box[3])
    origin = detectIntersection(line_matrix_left, line_matrix_right)
    angle = target_angle - option['angle']
    return [rotate(origin, point, angle) for point in mline_box]


def make_mline_boxes_options(mline_boxes: List) -> Tuple[int, int, List[Dict]]:
    options = []
    w_max = 0
    w_max_idx = -1
    for mline_idx, mline_box in enumerate(mline_boxes):
        w = distance(mline_box[0], mline_box[1])
        if w_max < w:
            w_max = w
            w_max_idx = mline_idx
        angle = (fline(mline_box[0], mline_box[1]))[2]
        options.append({
            'w': w,
            'angle': angle
        })
    return w_max, w_max_idx, options


def fix_mline_boxes_angle(mline_boxes: List) -> Tuple[List, float]:
    max_delta_angle = 7
    w_max, w_max_idx, options = make_mline_boxes_options(mline_boxes)
    target_angle = options[w_max_idx]['angle']
    for mline_idx, mline_box in enumerate(mline_boxes):
        if abs(target_angle - options[mline_idx]['angle']) > max_delta_angle:
            mline_boxes[mline_idx] = fix_box_angle(target_angle, mline_box, options[mline_idx])
    return mline_boxes, target_angle


def check_line_side_faces(target_points: np.ndarray, shape: Tuple) -> Tuple[List, Dict]:
    """
    Неработающая заглушка
    которая должна фиксить угол наклона боковых граней.
    """
    w = shape[1]
    out_of_bounds_points = []
    out_of_bounds_points_idx = {}
    for idx, point in enumerate(target_points):
        if point[0] < 0 or point[0] > w:
            out_of_bounds_points.append(idx)
            out_of_bounds_points_idx[idx] = True
        else:
            out_of_bounds_points_idx[idx] = False
    return out_of_bounds_points, out_of_bounds_points_idx


def get_center_point(p0: List, p1: List) -> List[float]:
    """
    Ищем середину отрезка, заданного 2 точками
    :param p0:
    :param p1:
    :return:
    """
    return [(p0[0]+p1[0])/2, (p0[1]+p1[1])/2]


def calc_diff(p1: List, p2: np.ndarray) -> Tuple[float, float]:
    return p1[0]-p2[0], p1[1]-p2[1]


def apply_new_point(point: List, dx: float, dy: float) -> List[float]:
    return [point[0]+dx, point[1]+dy]


def apply_new_box_angle(box: List, dx: float, dy: float) -> List[np.ndarray]:
    left_reference_point = get_center_point(box[3], box[0])
    right_reference_point = get_center_point(box[1], box[2])
    top_matrix = linearLineMatrix(box[0], box[1])
    bottom_matrix = linearLineMatrix(box[3], box[2])

    left_matrix = linearLineMatrix(left_reference_point, apply_new_point(left_reference_point, dx, dy))
    right_matrix = linearLineMatrix(right_reference_point, apply_new_point(right_reference_point, dx, dy))

    return [
        detectIntersection(left_matrix, top_matrix),
        detectIntersection(top_matrix, right_matrix),
        detectIntersection(right_matrix, bottom_matrix),
        detectIntersection(bottom_matrix, left_matrix)
    ]


def build_new_points(left_reference_point: List, right_reference_point: List, dx: float, dy: float) -> List[List]:
    return [
        apply_new_point(left_reference_point, dx, dy),
        apply_new_point(left_reference_point, -dx, -dy),
        apply_new_point(right_reference_point, -dx, -dy),
        apply_new_point(right_reference_point, dx, dy)
    ]


def fit_to_frame(target_points: np.ndarray, mline_boxes: List,  shape: Tuple) -> Tuple[List, List]:
    """
    Неработающая заглушка
    которая должна вписывать область с текстом в заданную рамку
    """
    h = shape[0]
    w = shape[1]
    out_of_bounds_points, out_of_bounds_points_idx = check_line_side_faces(target_points, shape)
    if len(out_of_bounds_points):
        left_reference_point = get_center_point(target_points[0], target_points[1])
        right_reference_point = get_center_point(target_points[2], target_points[3])
        reference_point_angle = (fline(left_reference_point, right_reference_point))[2]
        center_matrix = linearLineMatrix(left_reference_point, right_reference_point)
        top_matrix = linearLineMatrix(target_points[1], target_points[2])
        bottom_matrix = linearLineMatrix(target_points[0], target_points[3])
        if left_reference_point[0] < 0:
            left_reference_point = [0, getYByMatrix(center_matrix, 0)]
        if right_reference_point[0] > w:
            right_reference_point = [w, getYByMatrix(center_matrix, w)]
        if reference_point_angle > 0:
            p2_new = detectIntersection(top_matrix, linearLineMatrix([w, 0], [w, h]))
            p0_new = detectIntersection(bottom_matrix, linearLineMatrix([0, 0], [0, h]))
            p2_dx = w - right_reference_point[0]
            p0_dx = left_reference_point[0]
            if p2_dx > p0_dx:
                dx, dy = calc_diff(left_reference_point, p0_new)
            else:
                dx, dy = calc_diff(right_reference_point, p2_new)
                dx = -dx
                dy = -dy
        else:
            p3_new = detectIntersection(bottom_matrix, linearLineMatrix([w, 0], [w, h]))
            p1_new = detectIntersection(top_matrix, linearLineMatrix([0, 0], [0, h]))
            p3_dx = w - right_reference_point[0]
            p1_dx = left_reference_point[0]
            if p3_dx > p1_dx:
                dx, dy = calc_diff(left_reference_point, p1_new)
            else:
                dx, dy = calc_diff(right_reference_point, p3_new)
                dx = -dx
                dy = -dy
        target_points = build_new_points(left_reference_point, right_reference_point, dx, dy)
        mline_boxes = [apply_new_box_angle(mline_box, dx, dy) for mline_box in mline_boxes]
    return target_points, mline_boxes


def make_boxes(img: np.ndarray,
               boxes: List,
               color: Tuple[int, int, int] = (0, 0, 255),
               thickness: int = 2) -> np.ndarray:
    for box in boxes:
        polybox = np.array(box).astype(np.int32).reshape((-1))
        polybox = polybox.reshape(-1, 2)
        cv2.polylines(img, [polybox.reshape((-1, 1, 2))], True, color, thickness)
    return img


def resize(img: np.ndarray, scale_coef: float) -> np.ndarray:
    width = int(img.shape[1] * scale_coef)
    height = int(img.shape[0] * scale_coef)
    dim = (width, height)
    return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)


def resize_coordinates(points_arr: List, scale_coef: float) -> List:
    return [np.round(np.array(points)*scale_coef).tolist() for points in points_arr]


class CCraft(object):
    def multiline_to_one_line(self,
                              all_mline_boxes_rect: List,
                              image_parts: List[np.ndarray],
                              region_names: List[str],
                              multiply_coef: float = 1) -> Tuple:

        res = [self.make_one_line_from_many(mline_boxes,
                                            image_part,
                                            region_name,
                                            multiply_coef)
               for mline_boxes, image_part, region_name in zip(all_mline_boxes_rect, image_parts, region_names)]
        return ([item[0] for item in res],
                [item[1] for item in res],
                [item[2] for item in res])

    @staticmethod
    def make_one_line_from_many(mline_boxes: List,
                                image_part: np.ndarray,
                                region_name: str,
                                multiply_coef: float = 1) -> Tuple[np.ndarray, List, List]:

        if len(mline_boxes) > 1:
            mline_boxes, target_angle = fix_mline_boxes_angle(mline_boxes)
            target_points = minimum_bounding_rectangle(np.concatenate(mline_boxes, axis=0))
            target_points = normalize_multiline_rect(target_points, mline_boxes)
            target_points, mline_boxes = fit_to_frame(target_points, mline_boxes, image_part.shape)
            multiline_converter = MultilineConverter(image_part, mline_boxes, target_points)
            one_line_img = multiline_converter.covert_to_1_line(region_name)
        else:
            one_line_img = image_part
            target_points = []
        return (one_line_img,
                resize_coordinates([target_points], 1 / multiply_coef),
                resize_coordinates(mline_boxes, 1 / multiply_coef))


def convert_multiline_to_one_line(img,
                                  zones,
                                  all_mline_boxes,
                                  target_boxes,
                                  count_lines,
                                  region_names, ccraft=CCraft()):
    # convert multiline to one line
    image_parts = [img[int(box[1]):int(box[3]), int(box[0]):int(box[2])]
                   for box, cl in zip(target_boxes, count_lines)
                   if cl > 1]
    all_mline_boxes_rect = [mline_boxes
                            for mline_boxes, cl in zip(all_mline_boxes, count_lines)
                            if cl > 1]
    region_names_rect = [region_name
                         for region_name, cl in zip(region_names, count_lines)
                         if cl > 1]
    index_rect = [i
                  for i, cl in enumerate(count_lines)
                  if cl > 1]
    (zones_rect,
     zones_target_points,
     zones_mline_boxes) = ccraft.multiline_to_one_line(all_mline_boxes_rect,
                                                       image_parts,
                                                       region_names_rect)
    for i, zone in zip(index_rect, zones_rect):
        zones[i] = zone
    return zones
