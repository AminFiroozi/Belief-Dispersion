import unittest
import tempfile
from pathlib import Path

import pandas as pd

from research.sentiment.build_validation_sample import (
    RATER_COLUMNS,
    blinded_sheet,
    select_sample,
    write_csv,
)
from research.sentiment.validate_ratings import validate_sheet
from research.sentiment.run_benchmarks import (
    finbert_rows,
    validate_deepseek_response,
    validate_input,
)


class ValidationPackageTests(unittest.TestCase):
    def test_sample_balances_routes_and_hides_metadata(self):
        rows = []
        for route in ("auto_accept", "model_review", "retain_other_unclear"):
            for number in range(8):
                rows.append({
                    "record_id": f"{route}-{number}",
                    "headline": f"Headline {route} {number}",
                    "duplicate_group_id": f"group-{route}-{number}",
                    "year": 2020 + number % 2,
                    "source": f"Source {number % 3}",
                    "origin": "student_news",
                    "published_utc": "2020-01-01T00:00:00Z",
                    "selective_route": route,
                    "topic_family_primary": "monetary_policy" if route != "retain_other_unclear" else "other_unclear",
                })
        sample = select_sample(pd.DataFrame(rows), {"auto_accept-0"}, 4)
        self.assertEqual(len(sample), 12)
        self.assertEqual(sample.groupby("selective_route").size().to_dict(), {
            "auto_accept": 4, "model_review": 4, "retain_other_unclear": 4,
        })
        self.assertEqual(sample.groupby("split").size().to_dict(), {"development": 6, "holdout": 6})
        self.assertNotIn("auto_accept-0", set(sample["record_id"]))
        sheet = blinded_sheet(sample, "rater_1")
        self.assertEqual(sheet.columns.tolist(), list(RATER_COLUMNS))
        self.assertTrue(sheet["equity_sentiment"].eq("").all())
        validate_input(sheet)

    def test_response_requires_exact_codes_and_order(self):
        item = {
            "sample_id": "one", "equity_sentiment": "C", "label_confidence": "M",
            "ambiguity_flag": "Y", "reviewer_notes": "Mixed implication",
        }
        self.assertEqual(validate_deepseek_response({"items": [item]}, ["one"])[0]["equity_sentiment"], "C")
        with self.assertRaises(ValueError):
            validate_deepseek_response({"items": [item]}, ["two"])
        with self.assertRaises(ValueError):
            validate_deepseek_response({"items": [{**item, "equity_sentiment": "F"}]}, ["one"])

    def test_finbert_score_uses_model_labels_not_position(self):
        def classify(texts, **kwargs):
            return [[
                {"label": "negative", "score": 0.2},
                {"label": "positive", "score": 0.7},
                {"label": "neutral", "score": 0.1},
            ] for _ in texts]

        result = finbert_rows([{"sample_id": "one", "headline": "A headline"}], classify)
        self.assertAlmostEqual(result[0]["expected_tone"], 0.5)
        self.assertAlmostEqual(sum(result[0][key] for key in ("p_positive", "p_neutral", "p_negative")), 1.0)

    def test_generator_preserves_an_edited_rater_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.csv"
            original = pd.DataFrame([{"sample_id": "one", "headline": "A headline", "equity_sentiment": ""}])
            write_csv(original, path)
            write_csv(original, path)
            edited = original.copy()
            edited.loc[0, "equity_sentiment"] = "B"
            edited.to_csv(path, index=False)
            with self.assertRaises(FileExistsError):
                write_csv(original, path)

    def test_completed_sheet_validation(self):
        original = pd.DataFrame([dict(zip(RATER_COLUMNS, ["one", "A headline", "", "", "", ""]))])
        completed = original.copy()
        completed.loc[0, ["equity_sentiment", "label_confidence", "ambiguity_flag"]] = ["U", "L", "Y"]
        validate_sheet(completed, original)
        completed.loc[0, "headline"] = "Different text"
        with self.assertRaises(ValueError):
            validate_sheet(completed, original)


if __name__ == "__main__":
    unittest.main()
