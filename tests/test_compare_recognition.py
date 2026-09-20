import unittest

from zijinhua_tekla.pipeline.compare import compare_recognition_to_truth


class CompareRecognitionTests(unittest.TestCase):
    def test_compare_scores_factory_row_against_model_labels(self):
        recognition = [
            {
                "零件名称": "A-P-1",
                "规格": "PL10*100",
                "长度": 200,
                "工序": "下料折弯",
                "形状分类": "异形主材",
                "predicted_role": "箱型柱主材壁板",
                "predicted_process": "下料折弯",
                "predicted_shape": "异形主材",
                "predicted_delivery": "组立用",
                "evidence": "截面主壁板",
            }
        ]
        truth = [
            {
                "构件名称": "A-GKZ-1",
                "零件名称": "A-P-1",
                "规格": "PL10*100",
                "长度": 200,
                "数量": 1,
                "工序": "下料",
                "形状分类": "异形",
            }
        ]
        part = {
            "partId": "1",
            "partPosition": "A-P-1",
            "name": "连接板",
            "profileString": "PL10*100",
            "thickness": 10,
            "obbDims": {"x": 200.0, "y": 100.0, "z": 10.0},
            "isPlateLike": True,
        }

        aligned = compare_recognition_to_truth(
            recognition,
            truth,
            {"A-P-1": [part]},
            [part],
            {},
            {},
            "A-GKZ-1",
            {"assemblies": []},
            None,
        )

        self.assertEqual(1, len(aligned))
        self.assertEqual("DIFF", aligned[0]["prediction_status"])
        self.assertEqual("箱型柱主材壁板", aligned[0]["predicted_role"])
        self.assertEqual("下料折弯", aligned[0]["predicted_process"])
        self.assertEqual("下料", aligned[0]["工序"])


if __name__ == "__main__":
    unittest.main()
