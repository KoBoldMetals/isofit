import numpy as np
from isofit.core.common import eps, combos, get_absorption, expand_path, load_spectrum, load_wavelen, spectral_response_function
from io import StringIO

def test_eps():
    assert eps == 1e-5


def test_combos():
    inds = np.array([[1, 2], [3, 4, 5]])
    result = np.array([[1, 3], [2, 3], [1, 4], [2, 4], [1, 5], [2, 5]])
    assert np.array_equal(combos(inds), result)

def test_load_wavelen():
    file = StringIO('0 0.37686 0.00557 \n 1 0.38187 0.00558 \n 2 0.38688 0.00558')
    wl_modified, fwhm_modified = load_wavelen(file)
    assert(wl_modified.ndim == 1)
    assert(fwhm_modified.ndim == 1)
    assert(wl_modified[0] > 100)

def test_get_absorption():
    file = StringIO('12e7,2e7,3e7,4e7,3e7\n16e7,3e7,8e7,5e7,12e7')
    wavelengths = np.array([13e7, 15e7])
    w_abscf_new, i_abscf_new = get_absorption(wavelengths, file)
    assert(w_abscf_new[0] == 1.25e7*np.pi)
    assert(i_abscf_new[0] == 1.5e7*np.pi)
    assert(w_abscf_new[1] == 1.75e7*np.pi)
    assert(i_abscf_new[1] == 2.5e7*np.pi)

def test_expand_path(): # -- backslash vs forward slash discrepancy
    assert(expand_path("NASA", "JPL") == "NASA\JPL")
    assert(expand_path("NASA", "/JPL") == "/JPL")

def test_spectral_response_function():
    response_range = np.array([10, 8])
    mu = 6.0
    sigma = -2.0
    srf = spectral_response_function(response_range, mu, sigma)
    assert(abs(srf[0] - 0.182425524) < 0.0000001)
    assert(abs(srf[1] - 0.817574476) < 0.0000001)

def test_load_spectrum():
    file = StringIO('0.123 0.132 0.426 \n 0.234 0.234 0.132 \n 0.123 0.423 0.435')
    spectrum_new, wavelength_new = load_spectrum(file)
    assert(wavelength_new.ndim == 1)
    assert(spectrum_new.ndim == 1)
    assert(wavelength_new[0] > 100)


