from src.core.campaign import CampaignSession


def test_new_game_builds_town_and_party() -> None:
    session = CampaignSession.new_game()

    assert session.town.name == "Asterhold"
    assert len(session.party) == 3
    assert "tavern" in session.town.facilities
    assert session.chapter == 1
    assert session.battle_index == 1


def test_recruit_unit_spends_funds_and_adds_member() -> None:
    session = CampaignSession.new_game()
    before_size = len(session.party)
    before_funds = session.town.funds

    recruited = session.recruit_unit()

    assert recruited is True
    assert len(session.party) == before_size + 1
    assert session.town.funds == before_funds - 1200


def test_battle_resolution_advances_time_and_generates_report() -> None:
    session = CampaignSession.new_game()

    report = session.resolve_current_battle()

    assert report.rounds >= 1
    assert session.day == 2
    assert session.last_report is report
    assert session.chapter >= 1
    assert session.battle_index >= 1


def test_game_over_when_party_eliminated() -> None:
    session = CampaignSession.new_game()

    for unit in session.party:
        unit.is_alive = False
        unit.current_hp = 0

    session.remove_dead_units()

    assert len(session.party) == 0


def test_new_game_creates_squad_plans() -> None:
    session = CampaignSession.new_game()

    assert len(session.squad_plans) >= 1
    assigned = sum(len(plan.unit_ids) for plan in session.squad_plans)
    assert assigned == len(session.party)


def test_move_unit_to_another_plan() -> None:
    session = CampaignSession.new_game()

    # Ensure we have at least two plans for this move test.
    if len(session.squad_plans) < 2:
        session.squad_plans.append(type(session.squad_plans[0])(id="sp_2", name="Reserve"))
        session._sync_squad_plans()

    source = session.squad_plans[0]
    unit_id = source.unit_ids[0]
    moved = session.move_unit_to_plan(unit_id, 1)

    assert moved is True
    assert unit_id in session.squad_plans[1].unit_ids


def test_cycle_role_and_tactic() -> None:
    session = CampaignSession.new_game()
    plan = session.squad_plans[0]

    old_role = plan.role
    old_tactic = plan.tactic
    session.cycle_squad_role(plan.id)
    session.cycle_squad_tactic(plan.id)

    assert plan.role != old_role
    assert plan.tactic != old_tactic
