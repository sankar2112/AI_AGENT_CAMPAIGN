from app.services import compliance


def test_guaranteed_return_claim_is_blocked():
    result = compliance.check("Guaranteed 20% returns on this fund. T&C apply.", "email")
    assert result.status == "fail"
    assert "Guarantee" in result.notes


def test_rate_not_present_in_offer_is_blocked():
    result = compliance.check("Home loans from 6.5% p.a. Terms and conditions apply.", "email", offer_details="Rates from 8.4% p.a.")
    assert result.status == "fail"
    assert "6.5%" in result.notes


def test_rate_quoted_from_offer_is_allowed():
    result = compliance.check(
        "Home loans from 8.4% p.a. for eligible applicants. T&C apply.", "email", offer_details="Rates from 8.4% p.a."
    )
    assert result.status == "pass"


def test_sms_length_limit():
    result = compliance.check("a" * 400, "sms")
    assert result.status == "fail"
    assert "length limit" in result.notes


def test_missing_disclaimer_warns():
    result = compliance.check("Hi Meera, your new card is ready. Activate in the app.", "email")
    assert result.status == "warn"


def test_social_post_length_limit():
    result = compliance.check("a" * 500, "social")
    assert result.status == "fail"


def test_print_leaflet_within_limit_passes():
    body = "HOME LOAN\n\nDear Meera,\n\nVisit your nearest branch to know more.\n\nT&C apply."
    assert compliance.check(body, "print").status == "pass"


def test_pan_in_body_is_blocked():
    result = compliance.check("Your PAN ABCDE1234F is on file. T&C apply.", "email")
    assert result.status == "fail"
