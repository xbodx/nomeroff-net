import sys
import os
from typing import List, Dict

import numpy as np

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import TextDetectors


class TextDetector(object):
    @classmethod
    def get_classname(cls: object) -> str:
        return cls.__name__

    def __init__(self,
                 prisets: Dict = None,
                 default_label: str = "eu_ua_2015",
                 default_lines_count: int = 1) -> None:
        if prisets is None:
            prisets = {}
        self.prisets = prisets

        self.detectors_map = {}
        self.detectors = []
        self.detectors_names = []

        self.default_label = default_label
        self.default_lines_count = default_lines_count

        i = 0
        for priset_name in self.prisets:
            priset = self.prisets[priset_name]
            for region in priset["for_regions"]:
                self.detectors_map[region] = i
            _label = priset_name
            if _label not in dir(TextDetectors):
                raise Exception("Text detector {} not in Text Detectors".format(_label))
            detector_class = getattr(getattr(TextDetectors, _label), _label)
            self.detectors.append(detector_class)
            self.detectors_names.append(_label)
            i += 1
        self.load()

    def load(self):
        for i, (detector_class, detector_name) in enumerate(zip(self.detectors, self.detectors_names)):
            detector = detector_class()
            detector.load(self.prisets[detector_name]['model_path'])
            self.detectors[i] = detector

    def get_avalible_module(self) -> List[str]:
        return self.detectors_names

    def predict(self,
                zones: List[np.ndarray],
                labels: List[str] = None,
                lines: List[int] = None,
                return_acc: bool = False) -> List:
        if labels is None:
            labels = []
        if lines is None:
            lines = []

        while len(labels) < len(zones):
            labels.append(self.default_label)
        while len(lines) < len(zones):
            lines.append(self.default_lines_count)

        predicted = {}

        order_all = []
        res_all = []
        i = 0
        scores = []
        for zone, label in zip(zones, labels):
            if label in self.detectors_map.keys():
                detector = self.detectors_map[label]
                if detector not in predicted.keys():
                    predicted[detector] = {"zones": [], "order": []}
                predicted[detector]["zones"].append(zone)
                predicted[detector]["order"].append(i)
            else:
                res_all.append("")
                order_all.append(i)
                scores.append([])
            i += 1

        for key in predicted.keys():
            if return_acc:
                buff_res, acc = self.detectors[int(key)].predict(predicted[key]["zones"], return_acc=return_acc)
                res_all = res_all + buff_res
                scores = scores + list(acc)
            else:
                
                res_all = res_all + self.detectors[int(key)].predict(predicted[key]["zones"], return_acc=return_acc)
            order_all = order_all + predicted[key]["order"]

        if return_acc:
            return [
                [x for _, x in sorted(zip(order_all, res_all), key=lambda pair: pair[0])],
                [x for _, x in sorted(zip(order_all, scores), key=lambda pair: pair[0])]
            ]
        return [x for _, x in sorted(zip(order_all, res_all), key=lambda pair: pair[0])]

    @staticmethod
    def get_static_module(name: str) -> object:
        return getattr(getattr(TextDetectors, name), name)()

    def get_acc(self, predicted: List, decode: List, regions: List[str]) -> List[List[float]]:
        acc = []
        for i, region in enumerate(regions):
            if self.detectors_map.get(region, None) is None or len(decode[i]) == 0:
                acc.append([0.])
            else:
                detector = self.detectors[int(self.detectors_map[region])]
                _acc = detector.get_acc([predicted[i]], [decode[i]])
                acc.append([float(_acc)])
        return acc

    def get_module(self, name: str) -> object:
        ind = self.detectors_names.index(name)
        return self.detectors[ind]
