import datetime

import pytest
from django_test_migrations.contrib.unittest_case import MigratorTestCase


@pytest.mark.migration_test
class TestRoundContributionTrackingMigration(MigratorTestCase):
    migrate_from = ("bidding_round", "0001_initial")
    migrate_to = ("bidding_round", "0002_track_round_contribution_changes")

    def prepare(self):
        period = self.old_state.apps.get_model(
            "wirgarten", "GrowingPeriod"
        ).objects.create(
            start_date=datetime.date(2027, 3, 1), end_date=datetime.date(2028, 2, 29)
        )
        self.timestamp = datetime.datetime(2026, 11, 6, tzinfo=datetime.UTC)
        self.round = self.old_state.apps.get_model(
            "bidding_round", "BiddingRound"
        ).objects.create(
            growing_period=period,
            name="Existing completed round",
            status="closed",
            end_at=self.timestamp,
            contracts_created_at=self.timestamp,
        )

    def test_existing_round_is_preserved_without_inventing_a_baseline(self):
        round_ = self.new_state.apps.get_model(
            "bidding_round", "BiddingRound"
        ).objects.get(pk=self.round.pk)
        self.assertEqual("Existing completed round", round_.name)
        self.assertEqual(self.timestamp, round_.contracts_created_at)
        self.assertFalse(round_.contribution_changes_tracked)
        self.assertEqual(
            0,
            self.new_state.apps.get_model(
                "bidding_round", "BiddingRoundContributionChange"
            ).objects.count(),
        )
