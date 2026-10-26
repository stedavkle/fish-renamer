import pytest

from src.filename_assembler import FilenameAssembler, parse_filename

BASIC = "NiMic_IDN-Bangka-HRS_2026-02-14_16-06-19_dive_S-A7IV_NKM00025"
IDENTITY_PREFIX = "Labridae-Sc_Chlorurus_spilurus_B_ok_IP_dark_zz_"


@pytest.mark.parametrize("stem, fmt, gps, tail", [
    (BASIC + "_N_", 'basic', 'N', ''),
    (BASIC + "_G_two fish", 'basic', 'G', 'two fish'),
    (BASIC + "_N", 'basic', 'N', ''),                 # legacy marker
    (BASIC + "_N copy", 'basic', 'N', ' copy'),       # legacy marker + Finder copy
    (BASIC, 'basic', '', ''),                         # legacy, no marker
    (IDENTITY_PREFIX + BASIC + "_N", 'identity', 'N', ''),
    (IDENTITY_PREFIX + BASIC + "_G_juv", 'identity', 'G', 'juv'),
])
def test_parse_marker_and_tail(stem, fmt, gps, tail):
    parsed, error = parse_filename(stem)
    assert error == ''
    assert (parsed.format, parsed.gps, parsed.tail) == (fmt, gps, tail)
    assert parsed.fields[13] == 'NKM00025'
    assert parsed.body.endswith('_NKM00025')


def test_parse_identity_takes_fields_verbatim():
    parsed, _ = parse_filename("Labridae-Sc_Scarus_species3_B_xx_ad_ty_zz_OldPh_XXX-Gone-SIT_"
                               "2026-02-14_17-13-55_dive_Q-OLDCAM_NKM00162_N_")
    assert parsed.fields == ('Labridae-Sc', 'Scarus', 'species3', 'xx', 'ad', 'ty', 'zz',
                             'OldPh', 'XXX-Gone-SIT', '2026-02-14', '17-13-55', 'dive',
                             'Q-OLDCAM', 'NKM00162')


def test_parse_basic_original_with_underscore():
    parsed, _ = parse_filename("NiMic_IDN-Bangka-HRS_2026-02-14_16-06-19_dive_S-A7IV__DSC0001_N_")
    assert parsed.fields[13] == '_DSC0001'


@pytest.mark.parametrize("stem, reason_part", [
    ("DST0960", "No date_time"),
    ("NiMic_2026-02-14_16-06-19_dive_S-A7IV_NKM00025_N_", "Date is field 2"),
    ("NiMic_IDN-Bangka-HRS_2026-02-14_16-06-19", "Missing activity"),
])
def test_parse_errors_name_the_problem(stem, reason_part):
    parsed, error = parse_filename(stem)
    assert parsed is None
    assert reason_part in error


class FakeData:
    def get_user_code(self, name):
        return {'Nico Michiels': 'NiMic'}.get(name, '')

    def get_divesite_string(self, area, site):
        return 'IDN-Bangka-HRS'


@pytest.fixture
def assembler():
    return FilenameAssembler(FakeData())


def test_basic_appends_new_marker(assembler):
    name = assembler.assemble_basic_filename("NKM00025", "2026-02-14_16-06-19", "Nico Michiels",
                                             ("Bangka", "Coral Eye HR South"), "dive", "S-A7IV")
    assert name == BASIC + "_N_"


def test_basic_refuses_processed_name(assembler):
    assert assembler.assemble_basic_filename(BASIC + "_N_", "2026-02-14_16-06-19", "Nico Michiels",
                                             ("Bangka", "x"), "dive", "S-A7IV") is None


@pytest.mark.parametrize("suffix, expected_suffix", [
    ("_N_", "_N_"),
    ("_G_two fish", "_G_two fish"),   # GPS marker and free text survive Identify
    ("_N", "_N_"),                    # legacy marker is upgraded
    ("", "_N_"),
])
def test_identity_keeps_gps_and_tail(assembler, suffix, expected_suffix):
    name = assembler.assemble_identity_filename(BASIC + suffix, "Labridae-Sc", "Scarus", "species3",
                                                "ok", "ad", "ty", "zz")
    assert name == "Labridae-Sc_Scarus_species3_B_ok_ad_ty_zz_" + BASIC + expected_suffix


def test_identity_refuses_identified_name(assembler):
    assert assembler.assemble_identity_filename(IDENTITY_PREFIX + BASIC + "_N_", "F", "G", "s",
                                                "ok", "ad", "ty", "zz") is None


def test_analyze_for_editing_finds_common_fields(assembler):
    fmt, is_same, values = assembler.analyze_files_for_editing(
        [BASIC + "_N_", BASIC.replace("NKM00025", "NKM00026") + "_G_"])
    assert fmt == 'basic'
    assert is_same[:7] == [False] * 7
    assert values[7:13] == ['NiMic', 'IDN-Bangka-HRS', '2026-02-14', '16-06-19', 'dive', 'S-A7IV']
    assert is_same[13] is False


def test_analyze_for_editing_rejects_mixed_formats(assembler):
    with pytest.raises(ValueError, match="Mixed"):
        assembler.analyze_files_for_editing([BASIC + "_N_", IDENTITY_PREFIX + BASIC + "_N_"])
