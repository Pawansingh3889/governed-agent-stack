import pytest

from drift_gate.types import Family, TypeChange, classify_type_change, parse_type


@pytest.mark.parametrize(
    "raw,name,family,precision,scale,length",
    [
        ("decimal(10,2)", "decimal", Family.DECIMAL, 10, 2, None),
        ("DECIMAL (10 , 2)", "decimal", Family.DECIMAL, 10, 2, None),
        ("int", "int", Family.INTEGER, None, None, None),
        ("nvarchar(50)", "nvarchar", Family.STRING, None, None, 50),
        ("nvarchar(max)", "nvarchar", Family.STRING, None, None, -1),
        ("text", "text", Family.STRING, None, None, -1),
        ("datetime2(7)", "datetime2", Family.TEMPORAL, None, None, None),
        ("uniqueidentifier", "uniqueidentifier", Family.UUID, None, None, None),
        ("geography", "geography", Family.OTHER, None, None, None),
    ],
)
def test_parse(raw, name, family, precision, scale, length):
    t = parse_type(raw)
    assert t.name == name
    assert t.family is family
    assert t.precision == precision
    assert t.scale == scale
    assert t.length == length


def test_parse_never_raises_on_junk():
    assert parse_type("").family is Family.OTHER
    assert parse_type(None).family is Family.OTHER
    assert parse_type("!!!(((").family is Family.OTHER


class TestNarrowing:
    """The cases that motivated the tool."""

    def test_decimal_to_int_is_family_change(self):
        # The headline case: a yield column silently losing its fraction.
        assert classify_type_change("decimal(10,2)", "int") is TypeChange.FAMILY_CHANGED

    def test_decimal_losing_scale_narrows(self):
        assert classify_type_change("decimal(10,2)", "decimal(10,0)") is TypeChange.NARROWED

    def test_decimal_losing_integral_capacity_narrows(self):
        # precision - scale drops from 8 to 6 even though precision grew.
        assert classify_type_change("decimal(10,2)", "decimal(10,4)") is TypeChange.NARROWED

    def test_decimal_widening(self):
        assert classify_type_change("decimal(10,2)", "decimal(12,2)") is TypeChange.WIDENED

    def test_decimal_identical(self):
        assert classify_type_change("decimal(10,2)", "DECIMAL(10, 2)") is TypeChange.NONE

    def test_bigint_to_int_narrows(self):
        assert classify_type_change("bigint", "int") is TypeChange.NARROWED

    def test_int_to_bigint_widens(self):
        assert classify_type_change("int", "bigint") is TypeChange.WIDENED

    def test_int_aliases_equivalent(self):
        assert classify_type_change("int", "integer") is TypeChange.NONE

    def test_varchar_shrinking_narrows(self):
        assert classify_type_change("varchar(100)", "varchar(50)") is TypeChange.NARROWED

    def test_varchar_growing_widens(self):
        assert classify_type_change("varchar(50)", "varchar(100)") is TypeChange.WIDENED

    def test_max_to_bounded_narrows(self):
        assert classify_type_change("nvarchar(max)", "nvarchar(4000)") is TypeChange.NARROWED

    def test_bounded_to_max_widens(self):
        assert classify_type_change("nvarchar(50)", "nvarchar(max)") is TypeChange.WIDENED

    def test_unicode_loss_narrows_even_at_equal_length(self):
        # nvarchar(50) -> varchar(50) is the same length and still loses data.
        assert classify_type_change("nvarchar(50)", "varchar(50)") is TypeChange.NARROWED

    def test_ascii_to_unicode_at_equal_length_is_not_narrowing(self):
        assert classify_type_change("varchar(50)", "nvarchar(50)") is not TypeChange.NARROWED

    def test_datetime_to_date_narrows(self):
        assert classify_type_change("datetime2", "date") is TypeChange.NARROWED

    def test_datetime_widening_is_recognised(self):
        assert classify_type_change("datetime", "datetime2") is TypeChange.WIDENED

    def test_string_to_number_is_family_change(self):
        assert classify_type_change("varchar(20)", "bigint") is TypeChange.FAMILY_CHANGED

    def test_unknown_type_change_is_never_blessed(self):
        # We do not understand these, so we refuse to call the change safe.
        assert classify_type_change("geography", "geometry") is TypeChange.UNKNOWN

    def test_unknown_identical_is_none(self):
        assert classify_type_change("geography", "geography") is TypeChange.NONE
