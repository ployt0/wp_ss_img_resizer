from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from scaler import ResolutionsList, ImgScaler


def combined_widths_and_heights(w, h):
    scaler = ImgScaler(w, h)
    widths_and_heights, thmb = scaler.get_widths_and_heights()
    if thmb:
        widths_and_heights.append(thmb)
    return sorted(widths_and_heights)


@pytest.mark.parametrize("source_size,expected_dims", [
    ((728, 450), [(150, 150), (300, 185)]),  # pip-options
    ((624, 298), [(150, 150), (300, 143)]),  # az-vm-options
    ((499, 329), [(150, 150), (300, 198)]),  # grade-a-server-daten-because-hsts
    ((743, 477), [(150, 150), (300, 193),]),  # grade-a-ssllabs-no-hsts-no-redirect80
    ((499, 285), [(150, 150), (300, 171)]),  # grade-b-server-daten-redirect-but-no-hsts
    ((1020, 741), [(150, 150), (300, 218), (768, 558)]),  # status.clouveo. webp
    ((300, 1200), [(75, 300), (150, 150), (256, 1024)]),  # lena_strip. webp
    ((901, 499), [(150, 150), (300, 166), (768, 425)]),  # ssllabs-ap-with-hsts-and-redirects
])
def test_get_widths_and_heights_202203(source_size, expected_dims):
    """
    In order to understand how WordPress rounds... have a ton of examples.
    """
    widths_and_heights = combined_widths_and_heights(*source_size)
    assert widths_and_heights == expected_dims


@pytest.mark.parametrize("source_size,expected_dims", [
    ((900, 1080), [(150, 150), (250, 300), (768, 922), (853, 1024),]),  # compressioncomparison. webp
    ((1024, 694), [(150, 150), (300, 203), (768, 521)]),  # flapjack_lifting. webp
])
def test_get_widths_and_heights_202202(source_size, expected_dims):
    # The 768 width demonstrates direction of rounding expected, the
    # calculation comes to 520.5, so we expect 521. Python round gives 520.
    widths_and_heights = combined_widths_and_heights(*source_size)
    assert widths_and_heights == expected_dims

@pytest.mark.parametrize("source_size,expected_dims", [
    ((1032, 480), [(150, 150), (300, 140), (768, 357), (1024, 476)]),  # steamed. webp
    ((1080, 424), [(150, 150), (300, 118), (768, 302), (1024, 402)]),  # how-it-looked-installed
    ((1219, 396), [(150, 150), (300, 97), (768, 249), (1024, 333)]),  # mitmproxy-screen
])
def test_get_widths_and_heights_202108(source_size, expected_dims):
    widths_and_heights = combined_widths_and_heights(*source_size)
    assert widths_and_heights == expected_dims


@pytest.mark.parametrize("source_size,expected_dims", [
    ((1024, 200), [(150, 150), (300, 59), (768, 150)]),
    ((200, 1024), [(59, 300), (150, 150)]),
    ((200, 300), [(150, 150)]),
    ((300, 200), [(150, 150)]),
    ((300, 400), [(150, 150), (225, 300)]),
    ((400, 300), [(150, 150), (300, 225)]),
    ((768, 100), [(150, 100), (300, 39)]),
    ((100, 100), []),
])
def test_get_widths_and_heights_202207(source_size, expected_dims):
    # Edge cases I hadn't previously explored.
    widths_and_heights = combined_widths_and_heights(*source_size)
    assert widths_and_heights == expected_dims


@pytest.mark.parametrize("source_size,expected_dims", [
    ((2560, 1440), [(150,150), (300,169), (768,432), (1024,576), (1536,864), (2048,1152)]),
    ((4000, 3000), [(150,150), (300,225), (768,576), (1024,768), (1536,1152), (2048,1536)]),
])
def test_get_widths_and_heights_v5_3(source_size, expected_dims):
    """
    Thought (2560,1920) was used but apparently not:

testswhite_300x400.png
testswhite_4000x3000-1024x768.png
testswhite_4000x3000-150x150.png
testswhite_4000x3000-1536x1152.png
testswhite_4000x3000-2048x1536.png
testswhite_4000x3000-300x225.png
testswhite_4000x3000-768x576.png
testswhite_4000x3000.png
    """
    widths_and_heights = combined_widths_and_heights(*source_size)
    assert widths_and_heights == expected_dims

@pytest.mark.parametrize("decimal,integer", [
    (0.5, 1),
    (1.5, 2),
    (2.5, 3),
    (12.5, 13),
    (101.5, 102),
])
def test_ResolutionsList_round_halves_up(decimal,integer):
    assert ResolutionsList.round(decimal) == integer

@pytest.mark.parametrize("decimal,integer", [
    (0.499, 0),
    (0.501, 1),
    (1.499, 1),
    (1.501, 2),
    (2.499, 2),
    (2.501, 3),
    (3.499, 3),
    (3.501, 4),
])
def test_ResolutionsList_round(decimal,integer):
    assert ResolutionsList.round(decimal) == integer

