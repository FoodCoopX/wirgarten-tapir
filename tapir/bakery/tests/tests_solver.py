# """
# Tests for the bread baking optimizer.

# Strategy: Since CP-SAT may return different valid solutions,
# we test PROPERTIES of the output rather than exact values.

# Run with: pytest test_bread_optimizer.py -v
# """

# from bread_optimizer import (
#     BakingPlanResult,
#     BreadInfo,
#     SlotInfo,
#     solve_bread_planning,
# )

# # ---------------------------------------------------------------------------
# # Fixtures / helpers
# # ---------------------------------------------------------------------------


# def make_bread(bread_id, name="Brot", pieces=None, can_span=False):
#     """Shorthand to create a BreadInfo."""
#     return BreadInfo(
#         bread_id=bread_id,
#         name=name,
#         pieces_per_stove_layer=pieces or [10],
#         can_span_sessions=can_span,
#     )


# def make_slot(slot_id, pickup=1, assigned=None, prefs=None):
#     """Shorthand to create a SlotInfo."""
#     return SlotInfo(
#         slot_id=slot_id,
#         pickup_location_id=pickup,
#         assigned_bread_id=assigned,
#         preferred_bread_ids=prefs or [],
#     )


# def assert_valid_solution(result, breads, slots, capacities):
#     """
#     Validate that a solution satisfies ALL constraints.
#     Call this on every non-None result.
#     """
#     assert isinstance(result, BakingPlanResult)

#     bread_map = {b.bread_id: b for b in breads}
#     fixed_slots = [s for s in slots if s.assigned_bread_id is not None]
#     unassigned_slots = [s for s in slots if s.assigned_bread_id is None]

#     # -- Every unassigned slot got exactly one bread --
#     for s in unassigned_slots:
#         assert (
#             s.slot_id in result.slot_assignments
#         ), f"Slot {s.slot_id} has no assignment"
#         assert (
#             result.slot_assignments[s.slot_id] in bread_map
#         ), f"Slot {s.slot_id} assigned to unknown bread {result.slot_assignments[s.slot_id]}"

#     # -- No fixed slot was reassigned --
#     for s in fixed_slots:
#         assert s.slot_id not in result.slot_assignments

#     # -- Total baked per bread == total demand --
#     demand = {}
#     for s in fixed_slots:
#         demand[s.assigned_bread_id] = demand.get(s.assigned_bread_id, 0) + 1
#     for s in unassigned_slots:
#         b_id = result.slot_assignments[s.slot_id]
#         demand[b_id] = demand.get(b_id, 0) + 1

#     for b_id, qty in result.bread_quantities.items():
#         assert qty == demand.get(
#             b_id, 0
#         ), f"Bread {b_id}: baked {qty} but demand is {demand.get(b_id, 0)}"

#     # -- Pickup location capacities respected --
#     dist = {}
#     for s in fixed_slots:
#         key = (s.assigned_bread_id, s.pickup_location_id)
#         dist[key] = dist.get(key, 0) + 1
#     for s in unassigned_slots:
#         b_id = result.slot_assignments[s.slot_id]
#         key = (b_id, s.pickup_location_id)
#         dist[key] = dist.get(key, 0) + 1

#     for (b_id, p_id), count in dist.items():
#         cap = capacities.get((b_id, p_id), 0)
#         assert (
#             count <= cap
#         ), f"Capacity exceeded: bread {b_id} at pickup {p_id}: {count} > {cap}"

#     # -- Stove layer constraints --
#     for session in result.stove_sessions:
#         assert len(session) <= 4, "Session has more than 4 layers"
#         for layer_info in session:
#             if layer_info is None:
#                 continue
#             b_id, qty = layer_info
#             bread = bread_map[b_id]
#             assert (
#                 qty in bread.pieces_per_stove_layer
#             ), f"Bread {b_id}: qty {qty} not in {bread.pieces_per_stove_layer}"

#     # -- Stove total matches baked total --
#     stove_totals = {}
#     for session in result.stove_sessions:
#         for layer_info in session:
#             if layer_info is None:
#                 continue
#             b_id, qty = layer_info
#             stove_totals[b_id] = stove_totals.get(b_id, 0) + qty

#     for b_id, qty in result.bread_quantities.items():
#         assert (
#             stove_totals.get(b_id, 0) == qty
#         ), f"Bread {b_id}: stove produces {stove_totals.get(b_id, 0)} but needs {qty}"

#     # -- can_span_sessions=False → all layers in one session --
#     for b_id, bread in bread_map.items():
#         if not bread.can_span_sessions:
#             sessions_with_bread = [
#                 i
#                 for i, session in enumerate(result.stove_sessions)
#                 if any(l is not None and l[0] == b_id for l in session)
#             ]
#             assert (
#                 len(sessions_with_bread) <= 1
#             ), f"Bread {b_id} (can_span=False) appears in {len(sessions_with_bread)} sessions"

#     # -- Preference hit count is accurate --
#     actual_hits = sum(
#         1
#         for s in unassigned_slots
#         if s.preferred_bread_ids
#         and result.slot_assignments[s.slot_id] in s.preferred_bread_ids
#     )
#     assert result.preference_hits == actual_hits


# # ---------------------------------------------------------------------------
# # Tests: basic feasibility
# # ---------------------------------------------------------------------------


# class TestFeasibility:
#     def test_simple_case_finds_solution(self):
#         """One bread, a few slots, plenty of capacity → must solve."""
#         breads = [make_bread(1, pieces=[5, 6])]
#         slots = [make_slot(i, pickup=1) for i in range(1, 6)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.total_slots == 5

#     def test_infeasible_capacity(self):
#         """Demand exceeds capacity at the only pickup location → None."""
#         breads = [make_bread(1, pieces=[10])]
#         # 10 slots but capacity is only 5
#         slots = [make_slot(i, pickup=1) for i in range(1, 11)]
#         capacities = {(1, 1): 5}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is None

#     def test_no_slots_returns_empty_plan(self):
#         """Zero demand → valid but empty solution."""
#         breads = [make_bread(1, pieces=[10])]
#         slots = []
#         capacities = {(1, 1): 50}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=2)

#         assert result is not None
#         assert result.total_slots == 0
#         assert result.sessions_used == 0


# # ---------------------------------------------------------------------------
# # Tests: constraint satisfaction
# # ---------------------------------------------------------------------------


# class TestConstraints:
#     def test_fixed_assignments_are_preserved(self):
#         """Slots with a chosen bread must keep that bread."""
#         breads = [make_bread(1, pieces=[5, 6]), make_bread(2, pieces=[5, 6])]
#         slots = [
#             make_slot(1, pickup=1, assigned=1),
#             make_slot(2, pickup=1, assigned=1),
#             make_slot(3, pickup=1),
#             make_slot(4, pickup=1),
#         ]
#         capacities = {(1, 1): 10, (2, 1): 10}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         # Fixed slots should NOT appear in slot_assignments
#         assert 1 not in result.slot_assignments
#         assert 2 not in result.slot_assignments

#     def test_capacity_per_pickup_location(self):
#         """Bread distribution must respect per-location caps."""
#         breads = [make_bread(1, pieces=[5, 6, 7, 8, 9, 10])]
#         # 10 slots split across 2 locations
#         slots = [make_slot(i, pickup=1) for i in range(1, 6)] + [
#             make_slot(i, pickup=2) for i in range(6, 11)
#         ]
#         capacities = {(1, 1): 5, (1, 2): 5}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)

#     def test_no_span_sessions_constraint(self):
#         """Bread with can_span=False must be baked in a single session."""
#         # Need enough demand that it *could* span 2 sessions if allowed
#         breads = [
#             make_bread(1, "NoSpan", pieces=[10, 11, 12], can_span=False),
#             make_bread(2, "Filler", pieces=[5, 6, 7, 8, 9, 10], can_span=True),
#         ]
#         # 30 slots of bread 1 (needs ~3 layers) + 10 of bread 2
#         slots = [make_slot(i, pickup=1, assigned=1) for i in range(1, 31)] + [
#             make_slot(i, pickup=1) for i in range(31, 41)
#         ]
#         capacities = {(1, 1): 50, (2, 1): 50}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         # The validator inside assert_valid_solution already checks this,
#         # but let's be explicit:
#         sessions_with_bread_1 = [
#             i
#             for i, session in enumerate(result.stove_sessions)
#             if any(l is not None and l[0] == 1 for l in session)
#         ]
#         assert len(sessions_with_bread_1) <= 1

#     def test_stove_layer_quantities_are_valid(self):
#         """Each layer must use one of the allowed quantities."""
#         breads = [make_bread(1, pieces=[7, 8, 9])]
#         slots = [make_slot(i, pickup=1) for i in range(1, 9)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)


# # ---------------------------------------------------------------------------
# # Tests: preference optimization
# # ---------------------------------------------------------------------------


# class TestPreferences:
#     def test_preferences_are_satisfied_when_possible(self):
#         """When capacity allows, all preference slots should get a preferred bread."""
#         breads = [
#             make_bread(1, pieces=[5, 6, 7, 8, 9, 10]),
#             make_bread(2, pieces=[5, 6, 7, 8, 9, 10]),
#         ]
#         # Everyone prefers bread 1, capacity allows it
#         slots = [make_slot(i, pickup=1, prefs=[1]) for i in range(1, 11)]
#         capacities = {(1, 1): 20, (2, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 10
#         # All should get bread 1
#         for s in slots:
#             assert result.slot_assignments[s.slot_id] == 1

#     def test_preferences_respected_over_arbitrary_assignment(self):
#         """With two breads, slots preferring bread 2 should get bread 2."""
#         breads = [
#             make_bread(1, pieces=[5, 6, 7, 8, 9, 10]),
#             make_bread(2, pieces=[5, 6, 7, 8, 9, 10]),
#         ]
#         slots = [make_slot(i, pickup=1, prefs=[1]) for i in range(1, 6)] + [
#             make_slot(i, pickup=1, prefs=[2]) for i in range(6, 11)
#         ]
#         capacities = {(1, 1): 20, (2, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 10

#     def test_partial_preference_satisfaction(self):
#         """When capacity forces a trade-off, at least some prefs are met."""
#         breads = [make_bread(1, pieces=[5]), make_bread(2, pieces=[5])]
#         # 10 slots all prefer bread 1, but capacity for bread 1 is only 5
#         slots = [make_slot(i, pickup=1, prefs=[1]) for i in range(1, 11)]
#         capacities = {(1, 1): 5, (2, 1): 5}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 5  # best possible: 5 out of 10

#     def test_multiple_preferences_increase_satisfaction(self):
#         """Members with multiple preferred breads should have higher chance."""
#         breads = [
#             make_bread(1, pieces=[3, 4, 5]),
#             make_bread(2, pieces=[3, 4, 5]),
#             make_bread(3, pieces=[3, 4, 5]),
#         ]
#         # All slots prefer any of the 3 breads — satisfaction should be 100%
#         slots = [make_slot(i, pickup=1, prefs=[1, 2, 3]) for i in range(1, 11)]
#         capacities = {(1, 1): 20, (2, 1): 20, (3, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 10

#     def test_no_preferences_still_works(self):
#         """Slots with no preferences should still get assigned something."""
#         breads = [make_bread(1, pieces=[5, 6, 7, 8, 9, 10])]
#         slots = [make_slot(i, pickup=1, prefs=[]) for i in range(1, 6)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 0
#         assert result.unassigned_with_prefs == 0


# # ---------------------------------------------------------------------------
# # Tests: stove efficiency
# # ---------------------------------------------------------------------------


# class TestStoveEfficiency:
#     def test_minimizes_sessions_as_tiebreaker(self):
#         """Given equal preference satisfaction, fewer sessions is better."""
#         # 10 breads, pieces_per_layer=[10] → exactly 1 layer needed, 1 session
#         breads = [make_bread(1, pieces=[10])]
#         slots = [make_slot(i, pickup=1) for i in range(1, 11)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.sessions_used == 1

#     def test_multiple_sessions_when_needed(self):
#         """If demand exceeds one session's capacity, use more sessions."""
#         # pieces=[10], 4 layers → max 40 per session. 50 slots → need 2 sessions
#         breads = [make_bread(1, pieces=[10], can_span=True)]
#         slots = [make_slot(i, pickup=1) for i in range(1, 51)]
#         capacities = {(1, 1): 100}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.sessions_used >= 2


# # ---------------------------------------------------------------------------
# # Tests: edge cases
# # ---------------------------------------------------------------------------


# class TestEdgeCases:
#     def test_all_slots_fixed(self):
#         """All slots pre-assigned → solver just plans the stove."""
#         breads = [make_bread(1, pieces=[5, 6])]
#         slots = [make_slot(i, pickup=1, assigned=1) for i in range(1, 6)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert len(result.slot_assignments) == 0
#         assert result.bread_quantities[1] == 5

#     def test_single_slot(self):
#         """Minimal case: one slot, one bread."""
#         breads = [make_bread(1, pieces=[1])]
#         slots = [make_slot(1, pickup=1)]
#         capacities = {(1, 1): 5}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=1)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.slot_assignments[1] == 1

#     def test_many_breads_few_slots(self):
#         """More bread types than slots → solver picks a subset."""
#         breads = [make_bread(i, pieces=[1, 2, 3]) for i in range(1, 8)]
#         slots = [make_slot(1, pickup=1, prefs=[3])]
#         capacities = {(i, 1): 10 for i in range(1, 8)}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         # Should pick bread 3 (the preferred one)
#         assert result.slot_assignments[1] == 3

#     def test_mixed_fixed_and_unassigned(self):
#         """Realistic mix of fixed, preferred, and no-preference slots."""
#         breads = [
#             make_bread(1, pieces=[5, 6, 7]),
#             make_bread(2, pieces=[4, 5, 6]),
#             make_bread(3, pieces=[8, 9, 10]),
#         ]
#         slots = [
#             make_slot(1, pickup=1, assigned=1),  # fixed
#             make_slot(2, pickup=1, assigned=2),  # fixed
#             make_slot(3, pickup=1, prefs=[1, 3]),  # prefers 1 or 3
#             make_slot(4, pickup=2, prefs=[2]),  # prefers 2
#             make_slot(5, pickup=2),  # no preference
#             make_slot(6, pickup=1, prefs=[3]),  # prefers 3
#             make_slot(7, pickup=2, assigned=3),  # fixed
#         ]
#         capacities = {
#             (1, 1): 10,
#             (1, 2): 10,
#             (2, 1): 10,
#             (2, 2): 10,
#             (3, 1): 10,
#             (3, 2): 10,
#         }

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=5)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         # 3 slots have preferences, all should be satisfiable
#         assert result.preference_hits == 3

#     def test_multiple_pickup_locations(self):
#         """Slots spread across several locations with different capacities."""
#         breads = [make_bread(1, pieces=[3, 4, 5, 6, 7, 8, 9, 10])]
#         slots = (
#             [make_slot(i, pickup=1) for i in range(1, 4)]
#             + [make_slot(i, pickup=2) for i in range(4, 7)]
#             + [make_slot(i, pickup=3) for i in range(7, 10)]
#         )
#         capacities = {(1, 1): 3, (1, 2): 3, (1, 3): 3}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)

#     def test_preferences_for_unavailable_bread(self):
#         """Preferences referencing a bread not in available_breads are ignored."""
#         breads = [make_bread(1, pieces=[5, 6, 7, 8, 9, 10])]
#         # Slots prefer bread 99 which doesn't exist this week
#         slots = [make_slot(i, pickup=1, prefs=[99]) for i in range(1, 6)]
#         capacities = {(1, 1): 20}

#         result = solve_bread_planning(breads, slots, capacities, max_sessions=3)

#         assert result is not None
#         assert_valid_solution(result, breads, slots, capacities)
#         assert result.preference_hits == 0
