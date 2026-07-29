from query_warden import Warden

POLICY = {
    "default_role": "operator",
    "domains": {
        "production": ["production", "waste_log"],
        "staff": ["staff"],
    },
    "roles": {
        "operator": {"allow_domains": ["production"], "deny_columns": ["hourly_rate", "salary"]},
        "analyst": {"allow_tables": ["*"]},
    },
}


def w():
    return Warden.from_dict(POLICY)


def test_allowed_table_in_domain():
    d = w().check("SELECT product_id, waste_kg FROM waste_log", role="operator")
    assert d.allowed, d.reason


def test_table_outside_domain_is_denied():
    d = w().check("SELECT name FROM staff", role="operator")
    assert not d.allowed
    assert "staff" in d.reason


def test_denied_column_is_blocked():
    d = w().check("SELECT name, hourly_rate FROM production", role="operator")
    assert not d.allowed
    assert "hourly_rate" in d.reason


def test_select_star_blocked_when_columns_are_denied():
    d = w().check("SELECT * FROM production", role="operator")
    assert not d.allowed
    assert "SELECT *" in d.reason


def test_count_star_is_not_treated_as_select_star():
    d = w().check("SELECT COUNT(*) FROM production", role="operator")
    assert d.allowed, d.reason


def test_wildcard_role_allows_everything():
    d = w().check("SELECT name, hourly_rate FROM staff", role="analyst")
    assert d.allowed, d.reason


def test_unknown_role_is_denied():
    d = w().check("SELECT 1", role="ghost")
    assert not d.allowed
    assert "unknown role" in d.reason


def test_default_role_is_used_when_none_given():
    d = w().check("SELECT name FROM staff")  # operator default; staff not allowed
    assert not d.allowed


def test_decision_is_truthy_when_allowed():
    assert bool(w().check("SELECT product_id FROM production", role="operator")) is True


def test_join_across_allowed_and_denied_tables_is_denied():
    sql = "SELECT p.product_id, s.name FROM production p JOIN staff s ON p.operator = s.id"
    d = w().check(sql, role="operator")
    assert not d.allowed
    assert "staff" in d.reason
