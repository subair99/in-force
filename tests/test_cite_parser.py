import pytest

from inforce.cite_parser import extract


def kinds(text):
    return [(c.kind, c.act or c.rule or c.topic, c.section, c.value, c.amount) for c in extract(text)]


def test_act_long_and_short_forms():
    got = kinds("Under the Personal Income Tax Act and CITA.")
    assert ("citation", "PITA", None, None, None) in got
    assert ("citation", "CITA", None, None, None) in got


def test_short_forms_are_case_sensitive():
    assert kinds("pita bread and a cita") == []


@pytest.mark.parametrize("text,section", [
    ("section 33 of the Personal Income Tax Act", "33"),
    ("Personal Income Tax Act, s. 33(1)", "33(1)"),
    ("NTA section 58", "58"),
])
def test_section_next_to_act(text, section):
    [c] = extract(text)
    assert c.section == section


def test_bare_mention_merges_into_sectioned_citation():
    [c] = extract("section 33 of the Personal Income Tax Act (PITA)")
    assert (c.act, c.section, c.mentions) == ("PITA", "33", 2)


def test_repeated_concept_is_one_claim():
    [c] = extract("The CRA is generous. Consolidated Relief Allowance again. CRA.")
    assert (c.rule, c.mentions) == ("ng.pit.cra.old", 3)


def test_band_figure_with_amount():
    [c] = extract("the first ₦300,000 is taxed at 7%")
    assert (c.topic, c.value, c.amount) == ("pit_band", 0.07, "300000")


@pytest.mark.parametrize("text", ["first NGN 800,000 at 0%", "next N300,000 @ 11%", "first ₦ 300000 at 7 %"])
def test_band_figure_variants(text):
    [c] = extract(text)
    assert c.topic == "pit_band"


def test_cgt_figure():
    cs = [c for c in extract("companies pay capital gains tax at 10% of the gain") if c.kind == "figure"]
    assert [(c.topic, c.value) for c in cs] == [("cgt", 0.1)]


def test_percent_without_shape_is_ignored():
    assert extract("Inflation was 20% last year; VAT is everywhere.") == []


def test_line_numbers():
    [c] = extract("intro\n\nunder PITA")
    assert c.line == 3
