import unittest

import numpy as np
import pandas as pd

from research.topic_discovery.avalai_neutralize import json_hash, validate_items
from research.topic_discovery.assign_topic_families import (
    DEFAULT_TAXONOMY as DEFAULT_TAXONOMY_V2,
    combine_assignments,
    load_taxonomy_v2,
)
from research.topic_discovery.build_corpus import (
    assign_topics,
    deterministic_neutral_text,
    load_taxonomy,
    normalize_source,
)
from research.topic_discovery.cluster_stories import (
    DEFAULT_TAXONOMY,
    cluster_online,
    make_pair_audit,
    stratified_sample,
)
from research.topic_discovery.build_topic_validation import (
    headline_rater_sheet,
    pair_rater_sheet,
)
from research.topic_discovery.build_human_verification import (
    headline_verification_sheet,
    pair_verification_sheet,
)
from research.topic_discovery.topic_window_coverage import map_to_next_session


class CanonicalCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy(DEFAULT_TAXONOMY)

    def test_source_aliases_are_normalized(self):
        self.assertEqual(normalize_source("NYTimes"), "The New York Times")
        self.assertEqual(normalize_source(" Guardian "), "The Guardian")

    def test_candidate_geopolitical_topic_is_primary(self):
        primary, topics, matches = assign_topics(
            "Diplomats discuss regional developments",
            "iran_israel_direct_conflict",
            self.taxonomy,
        )
        self.assertEqual(primary, "geopolitics_conflict")
        self.assertIn("geopolitics_conflict", topics)
        self.assertIn("candidate:iran_israel_direct_conflict", matches)

    def test_baseline_neutralization_removes_directional_word(self):
        result = deterministic_neutral_text(
            "Oil surges after regional attack", self.taxonomy["neutral_replacements"]
        )
        self.assertNotIn("surges", result.casefold())
        self.assertIn("changes", result.casefold())


class StoryClusteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy(DEFAULT_TAXONOMY)

    def sample_frame(self):
        return pd.DataFrame(
            [
                {
                    "record_id": "a",
                    "headline": "Iran launches missiles toward Israel",
                    "source": "One",
                    "published_utc": "2024-04-13T00:00:00+00:00",
                    "primary_topic": "geopolitics_conflict",
                    "origin": "test",
                    "year": 2024,
                },
                {
                    "record_id": "b",
                    "headline": "Iranian missile attack targets Israel",
                    "source": "Two",
                    "published_utc": "2024-04-14T00:00:00+00:00",
                    "primary_topic": "geopolitics_conflict",
                    "origin": "test",
                    "year": 2024,
                },
                {
                    "record_id": "c",
                    "headline": "Ukraine discusses grain exports",
                    "source": "Three",
                    "published_utc": "2024-04-14T00:00:00+00:00",
                    "primary_topic": "geopolitics_conflict",
                    "origin": "test",
                    "year": 2024,
                },
            ]
        )

    def test_online_cluster_groups_similar_vectors_without_lookahead(self):
        frame = self.sample_frame()
        embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        clustered = cluster_online(frame, embeddings, self.taxonomy)
        ids = clustered.set_index("record_id")["story_cluster_id"]
        self.assertEqual(ids["a"], ids["b"])
        self.assertNotEqual(ids["a"], ids["c"])

    def test_pair_audit_hides_cluster_metadata(self):
        frame = self.sample_frame()
        embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        clustered = cluster_online(frame, embeddings, self.taxonomy)
        audit, key = make_pair_audit(clustered, sample_size=2)
        self.assertEqual(
            audit.columns.tolist(),
            ["pair_id", "headline_a", "headline_b", "same_story", "confidence", "reviewer_notes"],
        )
        self.assertNotIn("story_cluster_id", audit.columns)
        self.assertIn("cluster_a", key.columns)

    def test_stratified_sample_is_deterministic_and_exact(self):
        frame = pd.concat([self.sample_frame()] * 4, ignore_index=True)
        frame["record_id"] = [f"row-{i}" for i in range(len(frame))]
        first = stratified_sample(frame, 7)
        second = stratified_sample(frame, 7)
        self.assertEqual(first["record_id"].tolist(), second["record_id"].tolist())
        self.assertEqual(len(first), 7)


class AvalAINeutralizationTests(unittest.TestCase):
    def test_request_hash_is_independent_of_object_key_order(self):
        self.assertEqual(json_hash({"a": 1, "b": 2}), json_hash({"b": 2, "a": 1}))

    def test_response_validation_preserves_ids_and_headlines(self):
        expected = {"a": "Oil rises after attack"}
        payload = {
            "items": [
                {
                    "record_id": "a",
                    "topic_neutral_text": "Oil-market reaction to an attack",
                    "entities": ["oil"],
                    "event_terms": ["attack"],
                }
            ]
        }
        result = validate_items(payload, expected)
        self.assertEqual(result[0]["headline"], expected["a"])
        self.assertEqual(result[0]["record_id"], "a")


class TopicFamilyV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy_v2(DEFAULT_TAXONOMY_V2)

    def test_taxonomy_uses_named_conflicts(self):
        topics = self.taxonomy["topic_families"]
        self.assertIn("russia_ukraine", topics)
        self.assertIn("iran_israel", topics)
        self.assertNotIn("geopolitics_conflict", topics)

    def test_candidate_signal_can_override_weak_semantic_match(self):
        width = len(self.taxonomy["topic_priority"])
        semantic = np.zeros((1, width), dtype=np.float32)
        hits = np.zeros((1, width), dtype=np.uint8)
        candidate = np.zeros((1, width), dtype=np.float32)
        topic_index = self.taxonomy["topic_priority"].index("russia_ukraine")
        candidate[0, topic_index] = 1
        result = combine_assignments(
            semantic, hits, candidate, ["candidate:russia_ukraine_war"], self.taxonomy
        )
        self.assertEqual(result.loc[0, "topic_family_primary"], "russia_ukraine")
        self.assertEqual(result.loc[0, "topic_assignment_method"], "retrieval_candidate")

    def test_headline_rater_sheet_hides_machine_assignment(self):
        sample = pd.DataFrame(
            [{"topic_sample_id": "TOPIC-a", "headline": "A headline", "topic_family_primary": "monetary_policy"}]
        )
        sheet = headline_rater_sheet(sample, "test")
        self.assertNotIn("topic_family_primary", sheet.columns)
        self.assertEqual(sheet.loc[0, "primary_topic"], "")

    def test_pair_rater_sheet_uses_topic_discourse_field(self):
        sample = pd.DataFrame(
            [
                {
                    "pair_id": "PAIR-a",
                    "record_a": {"headline": "First"},
                    "record_b": {"headline": "Second"},
                }
            ]
        )
        sheet = pair_rater_sheet(sample, "test")
        self.assertIn("same_topic_discourse", sheet.columns)
        self.assertNotIn("machine_relation", sheet.columns)

    def test_weekend_publication_maps_to_next_market_session(self):
        published = pd.Series(["2024-01-06T12:00:00Z"])
        market_dates = pd.DatetimeIndex(["2024-01-05", "2024-01-08"])
        mapped, valid = map_to_next_session(published, market_dates)
        self.assertTrue(valid[0])
        self.assertEqual(str(mapped[0]), "2024-01-08")

    def test_human_verification_preserves_agent_label(self):
        headline = pd.DataFrame(
            [
                {
                    "topic_sample_id": "TOPIC-a",
                    "headline": "A headline",
                    "primary_topic": "monetary_policy",
                    "secondary_topics": "inflation_prices",
                    "topic_centrality": "central",
                    "confidence": "high",
                    "reviewer_notes": "",
                }
            ]
        )
        review = headline_verification_sheet(headline)
        self.assertEqual(review.loc[0, "agent_primary_topic"], "monetary_policy")
        self.assertEqual(review.loc[0, "human_decision"], "")

    def test_pair_verification_has_explicit_correction_field(self):
        pair = pd.DataFrame(
            [
                {
                    "pair_id": "PAIR-a",
                    "headline_a": "First",
                    "headline_b": "Second",
                    "same_topic_discourse": "yes",
                    "confidence": "medium",
                    "reviewer_notes": "",
                }
            ]
        )
        review = pair_verification_sheet(pair)
        self.assertEqual(review.loc[0, "agent_same_topic_discourse"], "yes")
        self.assertIn("corrected_same_topic_discourse", review.columns)


if __name__ == "__main__":
    unittest.main()
