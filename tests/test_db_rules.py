import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.entities import Base, Camera, Rule
from src.db.rules import get_rules_by_id


CAMERA_1_PUBLIC_ID = uuid4()
CAMERA_2_PUBLIC_ID = uuid4()


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


@pytest.fixture
def populated_db(engine):
    with Session(engine) as session:
        camera1 = Camera(
            id=1, public_camera_id=CAMERA_1_PUBLIC_ID, owner_id=1,
            location="Front Door", created_at=datetime.now(timezone.utc))
        camera2 = Camera(
            id=2, public_camera_id=CAMERA_2_PUBLIC_ID, owner_id=1,
            location="Back Door", created_at=datetime.now(timezone.utc))
        rules = [
            Rule(id=1, public_rule_id=uuid4(), owner_id=1, camera_id=1,
                 rule="a person is present",
                 rule_nickname="Person Detection",
                 is_enabled=True, created_at=datetime.now(timezone.utc)),
            Rule(id=2, public_rule_id=uuid4(), owner_id=1, camera_id=1,
                 rule="a vehicle is present",
                 rule_nickname="Vehicle Detection",
                 is_enabled=True, created_at=datetime.now(timezone.utc)),
            Rule(id=3, public_rule_id=uuid4(), owner_id=1, camera_id=2,
                 rule="a dog is present", rule_nickname="Dog Detection",
                 is_enabled=True, created_at=datetime.now(timezone.utc)),
        ]
        session.add_all([camera1, camera2] + rules)
        session.commit()
    yield engine


def test_returns_all_rules_for_matching_camera(populated_db):
    rules = get_rules_by_id(str(CAMERA_1_PUBLIC_ID), populated_db)
    assert len(rules) == 2


def test_does_not_return_other_cameras_rules(populated_db):
    rules = get_rules_by_id(str(CAMERA_1_PUBLIC_ID), populated_db)
    assert all(r.camera_id == 1 for r in rules)


def test_returns_correct_rule_content(populated_db):
    rules = get_rules_by_id(str(CAMERA_1_PUBLIC_ID), populated_db)
    rule_texts = {r.rule for r in rules}
    assert rule_texts == {"a person is present", "a vehicle is present"}


def test_returns_single_rule_for_second_camera(populated_db):
    rules = get_rules_by_id(str(CAMERA_2_PUBLIC_ID), populated_db)
    assert len(rules) == 1
    assert rules[0].rule == "a dog is present"


def test_returns_empty_list_for_unknown_camera_id(populated_db):
    rules = get_rules_by_id(str(uuid4()), populated_db)
    assert rules == []


def test_returns_empty_list_when_camera_has_no_rules(engine):
    with Session(engine) as session:
        camera = Camera(
            id=1, public_camera_id=CAMERA_1_PUBLIC_ID, owner_id=1,
            location="Front Door", created_at=datetime.now(timezone.utc))
        session.add(camera)
        session.commit()
    rules = get_rules_by_id(str(CAMERA_1_PUBLIC_ID), engine)
    assert rules == []
