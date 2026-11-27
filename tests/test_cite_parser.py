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


@pytest.mark.parametrize("text,name", [
    ("The Stamp Duties Act requires duty on receipts.", "Stamp Duties Act"),
    ("Under the Petroleum Profits Tax Act.", "Petroleum Profits Tax Act"),
    ("the Federal Inland Revenue Service (Establishment) Act", "Federal Inland Revenue Service (Establishment) Act"),
    ("Personal Income Tax (Amendment) Act 2011", "Personal Income Tax (Amendment) Act"),
])
def test_other_tax_acts_are_citations(text, name):
    [c] = extract(text)
    assert (c.kind, c.act, c.text) == ("citation", name, name)


def test_known_act_names_are_not_doubled_by_the_catch_all():
    claims = extract("Under the Nigeria Tax Act and the Value Added Tax Act and IDITRA.")
    assert [c.act for c in claims] == ["NTA", "VAT Act", "IDITRA"]


@pytest.mark.parametrize("text", ["the tax act", "a Tax Act", "This Act imposes tax."])
def test_catch_all_needs_a_named_tax_act(text):
    assert extract(text) == []


@pytest.mark.parametrize("name", ["Deep Offshore and Inland Basin Act",
                                  "Deep Offshore and Inland Basin Production Sharing Contracts Act"])
def test_deep_offshore_act_under_both_titles(name):
    [c] = extract(f"Under the {name}, the tax ...")
    assert (c.kind, c.act, c.text) == ("citation", "Deep Offshore and Inland Basin Act", name)
