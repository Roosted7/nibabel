""" Testing parrec module
"""

from os.path import join as pjoin, dirname, basename
from glob import glob
from warnings import simplefilter

import numpy as np
from numpy import array as npa

from .. import load as top_load
from ..nifti1 import Nifti1Image, Nifti1Extension
from .. import parrec
from ..parrec import (parse_PAR_header, PARRECHeader, PARRECError, vol_numbers,
                      vol_is_full, PARRECImage, PARRECArrayProxy, exts2pars)
from ..openers import ImageOpener
from ..fileholders import FileHolder
from ..volumeutils import array_from_file

from numpy.testing import (assert_almost_equal,
                           assert_array_equal)

from nose.tools import (assert_true, assert_false, assert_raises,
                        assert_equal)

from ..testing import (clear_and_catch_warnings, suppress_warnings,
                       assert_arr_dict_equal)

from .test_arrayproxy import check_mmap
from . import test_spatialimages as tsi


DATA_PATH = pjoin(dirname(__file__), 'data')
EG_PAR = pjoin(DATA_PATH, 'phantom_EPI_asc_CLEAR_2_1.PAR')
EG_REC = pjoin(DATA_PATH, 'phantom_EPI_asc_CLEAR_2_1.REC')
with ImageOpener(EG_PAR, 'rt') as _fobj:
    HDR_INFO, HDR_DEFS = parse_PAR_header(_fobj)
# Fake truncated
TRUNC_PAR = pjoin(DATA_PATH, 'phantom_truncated.PAR')
TRUNC_REC = pjoin(DATA_PATH, 'phantom_truncated.REC')
# Post-processed diffusion: ADC Map
ADC_PAR = pjoin(DATA_PATH, 'ADC_Map.PAR')
# Fake V4
V4_PAR = pjoin(DATA_PATH, 'phantom_fake_v4.PAR')
# Fake V4.1
V41_PAR = pjoin(DATA_PATH, 'phantom_fake_v4_1.PAR')
# Fake V4.1 with dual TRs
DUAL_TR_PAR = pjoin(DATA_PATH, 'phantom_fake_dualTR.PAR')
# Anonymized PAR
ANON_PAR = pjoin(DATA_PATH, 'umass_anonymized.PAR')
# Fake varying scaling
VARY_PAR = pjoin(DATA_PATH, 'phantom_varscale.PAR')
VARY_REC = pjoin(DATA_PATH, 'phantom_varscale.REC')
# V4.2 PAR with variant field names in the header
VARIANT_PAR = pjoin(DATA_PATH, 'variant_v4_2_header.PAR')
# Affine as we determined it mid-2014
AN_OLD_AFFINE = np.array(
    [[-3.64994708, 0., 1.83564171, 123.66276611],
     [0., -3.75, 0., 115.617],
     [0.86045705, 0., 7.78655376, -27.91161211],
     [0., 0., 0., 1.]])
# Affine from Philips-created NIfTI
PHILIPS_AFFINE = np.array(
    [[-3.65, -0.0016, 1.8356, 125.4881],
     [0.0016, -3.75, -0.0004, 117.4916],
     [0.8604, 0.0002, 7.7866, -28.3411],
     [0., 0., 0., 1.]])

# Affines generated by parrec.py from test data in many orientations
# Data from http://psydata.ovgu.de/philips_achieva_testfiles/conversion2
PREVIOUS_AFFINES = {
    "Phantom_EPI_3mm_cor_20APtrans_15RLrot_SENSE_15_1":
    npa([[-3., 0., 0., 118.5],
         [0., -0.77645714, -3.18755523, 72.82738377],
         [0., -2.89777748, 0.85410285, 97.80720486],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_cor_SENSE_8_1":
    npa([[-3., 0., 0., 118.5],
         [0., 0., -3.3, 64.35],
         [0., -3., 0., 118.5],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_sag_15AP_SENSE_13_1":
    npa([[0., 0.77645714, 3.18755523, -92.82738377],
         [-3., 0., 0., 118.5],
         [0., -2.89777748, 0.85410285, 97.80720486],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_sag_15FH_SENSE_12_1":
    npa([[0.77645714, 0., 3.18755523, -92.82738377],
         [-2.89777748, 0., 0.85410285, 97.80720486],
         [0., -3., 0., 118.5],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_sag_15RL_SENSE_11_1":
    npa([[0., 0., 3.3, -64.35],
         [-2.89777748, -0.77645714, 0., 145.13226726],
         [0.77645714, -2.89777748, 0., 83.79215357],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_sag_SENSE_7_1":
    npa([[0., 0., 3.3, -64.35],
         [-3., 0., 0., 118.5],
         [0., -3., 0., 118.5],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_tra_-30AP_10RL_20FH_SENSE_14_1":
    npa([[0., 0., 3.3, -74.35],
         [-3., 0., 0., 148.5],
         [0., -3., 0., 138.5],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_tra_15FH_SENSE_9_1":
    npa([[0.77645714, 0., 3.18755523, -92.82738377],
         [-2.89777748, 0., 0.85410285, 97.80720486],
         [0., -3., 0., 118.5],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_tra_15RL_SENSE_10_1":
    npa([[0., 0., 3.3, -64.35],
         [-2.89777748, -0.77645714, 0., 145.13226726],
         [0.77645714, -2.89777748, 0., 83.79215357],
         [0., 0., 0., 1.]]),
    "Phantom_EPI_3mm_tra_SENSE_6_1":
    npa([[-3., 0., 0., 118.5],
         [0., -3., 0., 118.5],
         [0., 0., 3.3, -64.35],
         [0., 0., 0., 1.]]),
}
# Original values for b values in DTI.PAR, still in PSL orientation
DTI_PAR_BVECS = np.array([[-0.667, -0.667, -0.333],
                          [-0.333, 0.667, -0.667],
                          [-0.667, 0.333, 0.667],
                          [-0.707, -0.000, -0.707],
                          [-0.707, 0.707, 0.000],
                          [-0.000, 0.707, 0.707],
                          [0.000, 0.000, 0.000],
                          [0.000, 0.000, 0.000]])

# DTI.PAR values for bvecs
DTI_PAR_BVALS = [1000] * 6 + [0, 1000]

EXAMPLE_IMAGES = [
    # Parameters come from load of Philips' conversion to NIfTI
    # Loaded image was ``phantom_EPI_asc_CLEAR_2_1.nii`` from
    # http://psydata.ovgu.de/philips_achieva_testfiles/conversion
    dict(
        fname=EG_PAR,
        shape=(64, 64, 9, 3),
        dtype=np.uint16,
        # We disagree with Philips about the right affine, for the moment, so
        # use our own affine as determined from a previous load in nibabel
        affine=AN_OLD_AFFINE,
        zooms=(3.75, 3.75, 8.0, 2000.0),
        data_summary=dict(
            min=0.0,
            max=2299.4110643863678,
            mean=194.95876256117265),
        is_proxy=True)
]


def _shuffle(arr):
    """Return a copy of the array with entries shuffled.

    Needed to avoid a bug in np.random.shuffle for numpy 1.7.
    see:  numpy/numpy#4286
    """
    return arr[np.argsort(np.random.randn(len(arr)))]


def test_top_level_load():
    # Test PARREC images can be loaded from nib.load
    img = top_load(EG_PAR)
    assert_almost_equal(img.affine, AN_OLD_AFFINE)


def test_header():
    v42_hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    for strict_sort in [False, True]:
        with open(V4_PAR, 'rt') as fobj:
            v4_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=strict_sort)
        with open(V41_PAR, 'rt') as fobj:
            v41_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=strict_sort)
        for hdr in (v42_hdr, v41_hdr, v4_hdr):
            hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
            assert_equal(hdr.get_data_shape(), (64, 64, 9, 3))
            assert_equal(hdr.get_data_dtype(), np.dtype('<u2'))
            assert_equal(hdr.get_zooms(), (3.75, 3.75, 8.0, 2000.0))
            assert_equal(hdr.get_data_offset(), 0)
            si = np.array(
                [np.unique(x) for x in hdr.get_data_scaling()]).ravel()
            assert_almost_equal(si, (1.2903541326522827, 0.0), 5)
            assert_equal(hdr.get_q_vectors(), None)
            assert_equal(hdr.get_bvals_bvecs(), (None, None))


def test_header_scaling():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    def_scaling = [np.unique(x) for x in hdr.get_data_scaling()]
    fp_scaling = [np.unique(x) for x in hdr.get_data_scaling('fp')]
    dv_scaling = [np.unique(x) for x in hdr.get_data_scaling('dv')]
    # Check default is dv scaling
    assert_array_equal(def_scaling, dv_scaling)
    # And that it's almost the same as that from the converted nifti
    assert_almost_equal(dv_scaling, [[1.2903541326522827], [0.0]], 5)
    # Check that default for get_slope_inter is dv scaling
    for hdr in (hdr, PARRECHeader(HDR_INFO, HDR_DEFS)):
        scaling = [np.unique(x) for x in hdr.get_data_scaling()]
        assert_array_equal(scaling, dv_scaling)
    # Check we can change the default
    assert_false(np.all(fp_scaling == dv_scaling))


def test_header_volume_labels():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    # check volume labels
    vol_labels = hdr.get_volume_labels()
    assert_equal(list(vol_labels.keys()), ['dynamic scan number'])
    assert_array_equal(vol_labels['dynamic scan number'], [1, 2, 3])
    # check that output is ndarray rather than list
    assert_true(isinstance(vol_labels['dynamic scan number'], np.ndarray))


def test_orientation():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    assert_array_equal(HDR_DEFS['slice orientation'], 1)
    assert_equal(hdr.get_slice_orientation(), 'transverse')
    hdr_defc = hdr.image_defs
    hdr_defc['slice orientation'] = 2
    assert_equal(hdr.get_slice_orientation(), 'sagittal')
    hdr_defc['slice orientation'] = 3
    assert_equal(hdr.get_slice_orientation(), 'coronal')


def test_data_offset():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    assert_equal(hdr.get_data_offset(), 0)
    # Can set 0
    hdr.set_data_offset(0)
    # Can't set anything else
    assert_raises(PARRECError, hdr.set_data_offset, 1)


def test_affine():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    default = hdr.get_affine()
    scanner = hdr.get_affine(origin='scanner')
    fov = hdr.get_affine(origin='fov')
    assert_array_equal(default, scanner)
    # rotation part is same
    assert_array_equal(scanner[:3, :3], fov[:3, :3])
    # offset not
    assert_false(np.all(scanner[:3, 3] == fov[:3, 3]))
    # Regression test against what we were getting before
    assert_almost_equal(default, AN_OLD_AFFINE)
    # Test against RZS of Philips affine
    assert_almost_equal(default[:3, :3], PHILIPS_AFFINE[:3, :3], 2)


def test_affine_regression():
    # Test against checked affines from previous runs
    # Checked against Michael's data using some GUI tools
    # Data at http://psydata.ovgu.de/philips_achieva_testfiles/conversion2
    for basename, exp_affine in PREVIOUS_AFFINES.items():
        fname = pjoin(DATA_PATH, basename + '.PAR')
        with open(fname, 'rt') as fobj:
            hdr = PARRECHeader.from_fileobj(fobj)
        assert_almost_equal(hdr.get_affine(), exp_affine)


def test_get_voxel_size_deprecated():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    with clear_and_catch_warnings(modules=[parrec], record=True) as wlist:
        simplefilter('always')
        hdr.get_voxel_size()
    assert_equal(wlist[0].category, DeprecationWarning)


def test_get_sorted_slice_indices():
    # Test sorted slice indices
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    n_slices = len(HDR_DEFS)
    assert_array_equal(hdr.get_sorted_slice_indices(), range(n_slices))
    # Reverse - volume order preserved
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS[::-1])
    assert_array_equal(hdr.get_sorted_slice_indices(),
                       [8, 7, 6, 5, 4, 3, 2, 1, 0,
                        17, 16, 15, 14, 13, 12, 11, 10, 9,
                        26, 25, 24, 23, 22, 21, 20, 19, 18])
    # Omit last slice, only two volumes
    with clear_and_catch_warnings(modules=[parrec], record=True):
        hdr = PARRECHeader(HDR_INFO, HDR_DEFS[:-1], permit_truncated=True)
    assert_array_equal(hdr.get_sorted_slice_indices(), range(n_slices - 9))

    # different result when strict_sort=True
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS[::-1], strict_sort=True)
    assert_array_equal(hdr.get_sorted_slice_indices(), range(n_slices)[::-1])


def test_sorting_dual_echo_T1():
    # For this .PAR file, instead of getting 1 echo per volume, they get
    # mixed up unless strict_sort=True
    t1_par = pjoin(DATA_PATH, 'T1_dual_echo.PAR')
    with open(t1_par, 'rt') as fobj:
        t1_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=True)

    # should get the correct order even if we randomly shuffle the order
    t1_hdr.image_defs = _shuffle(t1_hdr.image_defs)

    sorted_indices = t1_hdr.get_sorted_slice_indices()
    sorted_echos = t1_hdr.image_defs['echo number'][sorted_indices]
    n_half = len(t1_hdr.image_defs) // 2
    # first half (volume 1) should all correspond to echo 1
    assert_equal(np.all(sorted_echos[:n_half] == 1), True)
    # second half (volume 2) should all correspond to echo 2
    assert_equal(np.all(sorted_echos[n_half:] == 2), True)

    # check volume labels
    vol_labels = t1_hdr.get_volume_labels()
    assert_equal(list(vol_labels.keys()), ['echo number'])
    assert_array_equal(vol_labels['echo number'], [1, 2])


def test_sorting_multiple_echos_and_contrasts():
    # This .PAR file has 3 echos and 4 image types (real, imaginary, magnitude,
    # phase).
    # After sorting should be:
        # Type 0, Echo 1, Slices 1-30
        # Type 0, Echo 2, Slices 1-30
        # Type 0, Echo 3, Slices 1-30
        # Type 1, Echo 1, Slices 1-30
        # ...
        # Type 3, Echo 3, Slices 1-30
    t1_par = pjoin(DATA_PATH, 'T1_3echo_mag_real_imag_phase.PAR')
    with open(t1_par, 'rt') as fobj:
        t1_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=True)

    # should get the correct order even if we randomly shuffle the order
    t1_hdr.image_defs = _shuffle(t1_hdr.image_defs)

    sorted_indices = t1_hdr.get_sorted_slice_indices()
    sorted_slices = t1_hdr.image_defs['slice number'][sorted_indices]
    sorted_echos = t1_hdr.image_defs['echo number'][sorted_indices]
    sorted_types = t1_hdr.image_defs['image_type_mr'][sorted_indices]

    ntotal = len(t1_hdr.image_defs)
    nslices = sorted_slices.max()
    nechos = sorted_echos.max()
    for slice_offset in range(ntotal//nslices):
        istart = slice_offset*nslices
        iend = (slice_offset+1)*nslices
        # innermost sort index is slices
        assert_array_equal(sorted_slices[istart:iend],
                           np.arange(1, nslices+1))
        current_echo = slice_offset % nechos + 1
        # same echo for each slice in the group
        assert_equal(np.all(sorted_echos[istart:iend] == current_echo),
                     True)
    # outermost sort index is image_type_mr
    assert_equal(np.all(sorted_types[:ntotal//4] == 0), True)
    assert_equal(np.all(sorted_types[ntotal//4:ntotal//2] == 1), True)
    assert_equal(np.all(sorted_types[ntotal//2:3*ntotal//4] == 2), True)
    assert_equal(np.all(sorted_types[3*ntotal//4:ntotal] == 3), True)

    # check volume labels
    vol_labels = t1_hdr.get_volume_labels()
    assert_equal(list(vol_labels.keys()), ['echo number', 'image_type_mr'])
    assert_array_equal(vol_labels['echo number'], [1, 2, 3]*4)
    assert_array_equal(vol_labels['image_type_mr'],
                       [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])


def test_sorting_multiecho_ASL():
    # For this .PAR file has 3 keys corresponding to volumes:
    #    'echo number', 'label type', 'dynamic scan number'
    asl_par = pjoin(DATA_PATH, 'ASL_3D_Multiecho.PAR')
    with open(asl_par, 'rt') as fobj:
        asl_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=True)

    # should get the correct order even if we randomly shuffle the order
    asl_hdr.image_defs = _shuffle(asl_hdr.image_defs)

    sorted_indices = asl_hdr.get_sorted_slice_indices()
    sorted_slices = asl_hdr.image_defs['slice number'][sorted_indices]
    sorted_echos = asl_hdr.image_defs['echo number'][sorted_indices]
    sorted_dynamics = asl_hdr.image_defs['dynamic scan number'][sorted_indices]
    sorted_labels = asl_hdr.image_defs['label type'][sorted_indices]
    ntotal = len(asl_hdr.image_defs)
    nslices = sorted_slices.max()
    nechos = sorted_echos.max()
    nlabels = sorted_labels.max()
    ndynamics = sorted_dynamics.max()
    assert_equal(nslices, 8)
    assert_equal(nechos, 3)
    assert_equal(nlabels, 2)
    assert_equal(ndynamics, 2)
    # check that dynamics vary slowest
    assert_array_equal(
        np.all(sorted_dynamics[:ntotal//ndynamics] == 1), True)
    assert_array_equal(
        np.all(sorted_dynamics[ntotal//ndynamics:ntotal] == 2), True)
    # check that labels vary 2nd slowest
    assert_array_equal(np.all(sorted_labels[:nslices*nechos] == 1), True)
    assert_array_equal(
        np.all(sorted_labels[nslices*nechos:2*nslices*nechos] == 2), True)
    # check that echos vary 2nd fastest
    assert_array_equal(np.all(sorted_echos[:nslices] == 1), True)
    assert_array_equal(np.all(sorted_echos[nslices:2*nslices] == 2), True)
    assert_array_equal(np.all(sorted_echos[2*nslices:3*nslices] == 3), True)
    # check that slices vary fastest
    assert_array_equal(sorted_slices[:nslices], np.arange(1, nslices+1))

    # check volume labels
    vol_labels = asl_hdr.get_volume_labels()
    assert_equal(list(vol_labels.keys()),
                 ['echo number', 'label type', 'dynamic scan number'])
    assert_array_equal(vol_labels['dynamic scan number'], [1]*6 + [2]*6)
    assert_array_equal(vol_labels['label type'], [1]*3 + [2]*3 + [1]*3 + [2]*3)
    assert_array_equal(vol_labels['echo number'], [1, 2, 3]*4)


def test_vol_number():
    # Test algorithm for calculating volume number
    assert_array_equal(vol_numbers([1, 3, 0]), [0, 0, 0])
    assert_array_equal(vol_numbers([1, 3, 0, 0]), [0, 0, 0, 1])
    assert_array_equal(vol_numbers([1, 3, 0, 0, 0]), [0, 0, 0, 1, 2])
    assert_array_equal(vol_numbers([1, 3, 0, 0, 4]), [0, 0, 0, 1, 0])
    assert_array_equal(vol_numbers([1, 3, 0, 3, 1, 0]),
                       [0, 0, 0, 1, 1, 1])
    assert_array_equal(vol_numbers([1, 3, 0, 3, 1, 0, 4]),
                       [0, 0, 0, 1, 1, 1, 0])
    assert_array_equal(vol_numbers([1, 3, 0, 3, 1, 0, 3, 1, 0]),
                       [0, 0, 0, 1, 1, 1, 2, 2, 2])


def test_vol_is_full():
    assert_array_equal(vol_is_full([3, 2, 1], 3), True)
    assert_array_equal(vol_is_full([3, 2, 1], 4), False)
    assert_array_equal(vol_is_full([4, 2, 1], 4), False)
    assert_array_equal(vol_is_full([3, 2, 4, 1], 4), True)
    assert_array_equal(vol_is_full([3, 2, 1], 3, 0), False)
    assert_array_equal(vol_is_full([3, 2, 0, 1], 3, 0), True)
    assert_raises(ValueError, vol_is_full, [2, 1, 0], 2)
    assert_raises(ValueError, vol_is_full, [3, 2, 1], 3, 2)
    assert_array_equal(vol_is_full([3, 2, 1, 2, 3, 1], 3),
                       [True] * 6)
    assert_array_equal(vol_is_full([3, 2, 1, 2, 3], 3),
                       [True, True, True, False, False])


def gen_par_fobj():
    for par in glob(pjoin(DATA_PATH, '*.PAR')):
        with open(par, 'rt') as fobj:
            yield par, fobj


def test_truncated_load():
    # Test loading of truncated header
    with open(TRUNC_PAR, 'rt') as fobj:
        gen_info, slice_info = parse_PAR_header(fobj)
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    with clear_and_catch_warnings(record=True) as wlist:
        PARRECHeader(gen_info, slice_info, True)
        assert_equal(len(wlist), 1)


def test_vol_calculations():
    # Test vol_is_full on sample data
    for par, fobj in gen_par_fobj():
        gen_info, slice_info = parse_PAR_header(fobj)
        slice_nos = slice_info['slice number']
        max_slice = gen_info['max_slices']
        assert_equal(set(slice_nos), set(range(1, max_slice + 1)))
        assert_array_equal(vol_is_full(slice_nos, max_slice), True)
        if par.endswith('NA.PAR'):
            continue  # Cannot parse this one
        # Load truncated without warnings
        with suppress_warnings():
            hdr = PARRECHeader(gen_info, slice_info, True)
        # Fourth dimension shows same number of volumes as vol_numbers
        shape = hdr.get_data_shape()
        d4 = 1 if len(shape) == 3 else shape[3]
        assert_equal(max(vol_numbers(slice_nos)), d4 - 1)


def test_diffusion_parameters():
    # Check getting diffusion parameters from diffusion example
    dti_par = pjoin(DATA_PATH, 'DTI.PAR')
    with open(dti_par, 'rt') as fobj:
        dti_hdr = PARRECHeader.from_fileobj(fobj)
    assert_equal(dti_hdr.get_data_shape(), (80, 80, 10, 8))
    assert_equal(dti_hdr.general_info['diffusion'], 1)
    bvals, bvecs = dti_hdr.get_bvals_bvecs()
    assert_almost_equal(bvals, DTI_PAR_BVALS)
    # DTI_PAR_BVECS gives bvecs copied from first slice each vol in DTI.PAR
    # Permute to match bvec directions to acquisition directions
    assert_almost_equal(bvecs, DTI_PAR_BVECS[:, [2, 0, 1]])
    # Check q vectors
    assert_almost_equal(dti_hdr.get_q_vectors(), bvals[:, None] * bvecs)


def test_diffusion_parameters_strict_sort():
    # Check getting diffusion parameters from diffusion example
    dti_par = pjoin(DATA_PATH, 'DTI.PAR')
    with open(dti_par, 'rt') as fobj:
        dti_hdr = PARRECHeader.from_fileobj(fobj, strict_sort=True)

    # should get the correct order even if we randomly shuffle the order
    dti_hdr.image_defs = _shuffle(dti_hdr.image_defs)

    assert_equal(dti_hdr.get_data_shape(), (80, 80, 10, 8))
    assert_equal(dti_hdr.general_info['diffusion'], 1)
    bvals, bvecs = dti_hdr.get_bvals_bvecs()
    assert_almost_equal(bvals, np.sort(DTI_PAR_BVALS))
    # DTI_PAR_BVECS gives bvecs copied from first slice each vol in DTI.PAR
    # Permute to match bvec directions to acquisition directions
    # note that bval sorting occurs prior to bvec sorting
    assert_almost_equal(bvecs,
                        DTI_PAR_BVECS[
                            np.ix_(np.argsort(DTI_PAR_BVALS), [2, 0, 1])])
    # Check q vectors
    assert_almost_equal(dti_hdr.get_q_vectors(), bvals[:, None] * bvecs)


def test_diffusion_parameters_v4():
    dti_v4_par = pjoin(DATA_PATH, 'DTIv40.PAR')
    with open(dti_v4_par, 'rt') as fobj:
        dti_v4_hdr = PARRECHeader.from_fileobj(fobj)
    assert_equal(dti_v4_hdr.get_data_shape(), (80, 80, 10, 8))
    assert_equal(dti_v4_hdr.general_info['diffusion'], 1)
    bvals, bvecs = dti_v4_hdr.get_bvals_bvecs()
    assert_almost_equal(bvals, DTI_PAR_BVALS)
    # no b-vector info in V4 .PAR files
    assert_equal(bvecs, None)
    assert_equal(dti_v4_hdr.get_q_vectors(), None)


def test_null_diffusion_params():
    # Test non-diffusion PARs return None for diffusion params
    for par, fobj in gen_par_fobj():
        if basename(par) in ('DTI.PAR', 'DTIv40.PAR', 'NA.PAR', 'ADC_Map.PAR'):
            continue
        gen_info, slice_info = parse_PAR_header(fobj)
        with suppress_warnings():
            hdr = PARRECHeader(gen_info, slice_info, True)
        assert_equal(hdr.get_bvals_bvecs(), (None, None))
        assert_equal(hdr.get_q_vectors(), None)


def test_epi_params():
    # Check EPI conversion
    for par_root in ('T2_-interleaved', 'T2_', 'phantom_EPI_asc_CLEAR_2_1'):
        epi_par = pjoin(DATA_PATH, par_root + '.PAR')
        with open(epi_par, 'rt') as fobj:
            epi_hdr = PARRECHeader.from_fileobj(fobj)
        assert_equal(len(epi_hdr.get_data_shape()), 4)
        assert_almost_equal(epi_hdr.get_zooms()[-1], 2000.0)


def test_truncations():
    # Test tests for truncation
    par = pjoin(DATA_PATH, 'T2_.PAR')
    with open(par, 'rt') as fobj:
        gen_info, slice_info = parse_PAR_header(fobj)
    # Header is well-formed as is
    hdr = PARRECHeader(gen_info, slice_info)
    assert_equal(hdr.get_data_shape(), (80, 80, 10, 2))
    # Drop one line, raises error
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info[:-1])
    # When we are permissive, we raise a warning, and drop a volume
    with clear_and_catch_warnings(modules=[parrec], record=True) as wlist:
        hdr = PARRECHeader(gen_info, slice_info[:-1], permit_truncated=True)
        assert_equal(len(wlist), 1)
    assert_equal(hdr.get_data_shape(), (80, 80, 10))
    # Increase max slices to raise error
    gen_info['max_slices'] = 11
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    gen_info['max_slices'] = 10
    hdr = PARRECHeader(gen_info, slice_info)
    # Increase max_echoes
    gen_info['max_echoes'] = 2
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    gen_info['max_echoes'] = 1
    hdr = PARRECHeader(gen_info, slice_info)
    # dyamics
    gen_info['max_dynamics'] = 3
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    gen_info['max_dynamics'] = 2
    hdr = PARRECHeader(gen_info, slice_info)
    # number of b values
    gen_info['max_diffusion_values'] = 2
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    gen_info['max_diffusion_values'] = 1
    hdr = PARRECHeader(gen_info, slice_info)
    # number of unique gradients
    gen_info['max_gradient_orient'] = 2
    assert_raises(PARRECError, PARRECHeader, gen_info, slice_info)
    gen_info['max_gradient_orient'] = 1
    hdr = PARRECHeader(gen_info, slice_info)


def test__get_uniqe_image_defs():
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS.copy())
    uip = hdr._get_unique_image_prop
    assert_equal(uip('image pixel size'), 16)
    # Make values not same - raise error
    hdr.image_defs['image pixel size'][3] = 32
    assert_raises(PARRECError, uip, 'image pixel size')
    assert_array_equal(uip('recon resolution'), [64, 64])
    hdr.image_defs['recon resolution'][4, 1] = 32
    assert_raises(PARRECError, uip, 'recon resolution')
    assert_array_equal(uip('image angulation'), [-13.26, 0, 0])
    hdr.image_defs['image angulation'][5, 2] = 1
    assert_raises(PARRECError, uip, 'image angulation')
    # This one differs from the outset
    assert_raises(PARRECError, uip, 'slice number')


def test_copy_on_init():
    # Test that input dict / array gets copied when making header
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    assert_false(hdr.general_info is HDR_INFO)
    hdr.general_info['max_slices'] = 10
    assert_equal(hdr.general_info['max_slices'], 10)
    assert_equal(HDR_INFO['max_slices'], 9)
    assert_false(hdr.image_defs is HDR_DEFS)
    hdr.image_defs['image pixel size'] = 8
    assert_array_equal(hdr.image_defs['image pixel size'], 8)
    assert_array_equal(HDR_DEFS['image pixel size'], 16)


def assert_structarr_equal(star1, star2):
    # Compare structured arrays (array_equal does not work for np 1.5)
    assert_equal(star1.dtype, star2.dtype)
    for name in star1.dtype.names:
        assert_array_equal(star1[name], star2[name])


def test_header_copy():
    # Test header copying
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    hdr2 = hdr.copy()

    def assert_copy_ok(hdr1, hdr2):
        assert_false(hdr1 is hdr2)
        assert_equal(hdr1.permit_truncated, hdr2.permit_truncated)
        assert_false(hdr1.general_info is hdr2.general_info)
        assert_arr_dict_equal(hdr1.general_info, hdr2.general_info)
        assert_false(hdr1.image_defs is hdr2.image_defs)
        assert_structarr_equal(hdr1.image_defs, hdr2.image_defs)

    assert_copy_ok(hdr, hdr2)
    assert_false(hdr.permit_truncated)
    assert_false(hdr2.permit_truncated)
    with open(TRUNC_PAR, 'rt') as fobj:
        assert_raises(PARRECError, PARRECHeader.from_fileobj, fobj)
    with open(TRUNC_PAR, 'rt') as fobj:
        trunc_hdr = PARRECHeader.from_fileobj(fobj, True)
    assert_true(trunc_hdr.permit_truncated)
    trunc_hdr2 = trunc_hdr.copy()
    assert_copy_ok(trunc_hdr, trunc_hdr2)


def test_image_creation():
    # Test parts of image API in parrec image creation
    hdr = PARRECHeader(HDR_INFO, HDR_DEFS)
    arr_prox_dv = np.array(PARRECArrayProxy(EG_REC, hdr, scaling='dv'))
    arr_prox_fp = np.array(PARRECArrayProxy(EG_REC, hdr, scaling='fp'))
    good_map = dict(image=FileHolder(EG_REC),
                    header=FileHolder(EG_PAR))
    trunc_map = dict(image=FileHolder(TRUNC_REC),
                     header=FileHolder(TRUNC_PAR))
    for func, good_param, trunc_param in (
            (PARRECImage.from_filename, EG_PAR, TRUNC_PAR),
            (PARRECImage.load, EG_PAR, TRUNC_PAR),
            (parrec.load, EG_PAR, TRUNC_PAR),
            (PARRECImage.from_file_map, good_map, trunc_map)):
        img = func(good_param)
        assert_array_equal(img.dataobj, arr_prox_dv)
        # permit_truncated is keyword only
        assert_raises(TypeError, func, good_param, False)
        img = func(good_param, permit_truncated=False)
        assert_array_equal(img.dataobj, arr_prox_dv)
        # scaling is keyword only
        assert_raises(TypeError, func, good_param, False, 'dv')
        img = func(good_param, permit_truncated=False, scaling='dv')
        assert_array_equal(img.dataobj, arr_prox_dv)
        img = func(good_param, scaling='dv')
        assert_array_equal(img.dataobj, arr_prox_dv)
        # Can use fp scaling
        img = func(good_param, scaling='fp')
        assert_array_equal(img.dataobj, arr_prox_fp)
        # Truncated raises error without permit_truncated=True
        assert_raises(PARRECError, func, trunc_param)
        assert_raises(PARRECError, func, trunc_param, permit_truncated=False)
        img = func(trunc_param, permit_truncated=True)
        assert_array_equal(img.dataobj, arr_prox_dv)
        img = func(trunc_param, permit_truncated=True, scaling='dv')
        assert_array_equal(img.dataobj, arr_prox_dv)
        img = func(trunc_param, permit_truncated=True, scaling='fp')
        assert_array_equal(img.dataobj, arr_prox_fp)


class FakeHeader(object):
    """ Minimal API of header for PARRECArrayProxy
    """

    def __init__(self, shape, dtype):
        self._shape = shape
        self._dtype = np.dtype(dtype)

    def get_data_shape(self):
        return self._shape

    def get_data_dtype(self):
        return self._dtype

    def get_sorted_slice_indices(self):
        n_slices = np.prod(self._shape[2:])
        return np.arange(n_slices)

    def get_data_scaling(self, scaling):
        scale_shape = (1, 1) + self._shape[2:]
        return np.ones(scale_shape), np.zeros(scale_shape)

    def get_rec_shape(self):
        n_slices = np.prod(self._shape[2:])
        return self._shape[:2] + (n_slices,)


def test_parrec_proxy():
    # Test PAR / REC proxy class, including mmap flags
    shape = (10, 20, 30, 5)
    hdr = FakeHeader(shape, np.int32)
    check_mmap(hdr, 0, PARRECArrayProxy,
               has_scaling=True,
               unscaled_is_view=False)


class TestPARRECImage(tsi.MmapImageMixin):
    image_class = PARRECImage
    check_mmap_mode = False

    def get_disk_image(self):
        # The example image does have image scaling to apply
        return parrec.load(EG_PAR), EG_PAR, True


def test_bitpix():
    # Check errors for other than 8, 16 bit
    hdr_defs = HDR_DEFS.copy()
    for pix_size in (24, 32):
        hdr_defs['image pixel size'] = pix_size
        assert_raises(PARRECError, PARRECHeader, HDR_INFO, hdr_defs)


def test_varying_scaling():
    # Check the algorithm works as expected for varying scaling
    img = PARRECImage.load(VARY_REC)
    rec_shape = (64, 64, 27)
    with open(VARY_REC, 'rb') as fobj:
        arr = array_from_file(rec_shape, '<i2', fobj)
    img_defs = img.header.image_defs
    slopes = img_defs['rescale slope']
    inters = img_defs['rescale intercept']
    sc_slopes = img_defs['scale slope']
    # Check dv scaling
    scaled_arr = arr.astype(np.float64)
    for i in range(arr.shape[2]):
        scaled_arr[:, :, i] *= slopes[i]
        scaled_arr[:, :, i] += inters[i]
    assert_almost_equal(np.reshape(scaled_arr, img.shape, order='F'),
                        img.get_data(), 9)
    # Check fp scaling
    for i in range(arr.shape[2]):
        scaled_arr[:, :, i] /= (slopes[i] * sc_slopes[i])
    dv_img = PARRECImage.load(VARY_REC, scaling='fp')
    assert_almost_equal(np.reshape(scaled_arr, img.shape, order='F'),
                        dv_img.get_data(), 9)


def test_anonymized():
    # Test we can read anonymized PAR correctly
    with open(ANON_PAR, 'rt') as fobj:
        anon_hdr = PARRECHeader.from_fileobj(fobj)
    gen_defs, img_defs = anon_hdr.general_info, anon_hdr.image_defs
    assert_equal(gen_defs['patient_name'], '')
    assert_equal(gen_defs['exam_name'], '')
    assert_equal(gen_defs['protocol_name'], '')
    assert_equal(gen_defs['series_type'], 'Image   MRSERIES')
    assert_almost_equal(img_defs['window center'][0], -2374.72283272283, 6)
    assert_almost_equal(img_defs['window center'][-1], 236.385836385836, 6)
    assert_almost_equal(img_defs['window width'][0], 767.277167277167, 6)
    assert_almost_equal(img_defs['window width'][-1], 236.385836385836, 6)


def test_exts2par():
    # Test we can load PAR headers from NIfTI extensions
    par_img = PARRECImage.from_filename(EG_PAR)
    nii_img = Nifti1Image.from_image(par_img)
    assert_equal(exts2pars(nii_img), [])
    assert_equal(exts2pars(nii_img.header), [])
    assert_equal(exts2pars(nii_img.header.extensions), [])
    assert_equal(exts2pars([]), [])
    # Add a header extension
    with open(EG_PAR, 'rb') as fobj:
        hdr_dump = fobj.read()
        dump_ext = Nifti1Extension('comment', hdr_dump)
    nii_img.header.extensions.append(dump_ext)
    hdrs = exts2pars(nii_img)
    assert_equal(len(hdrs), 1)
    # Test attribute from PARRECHeader
    assert_equal(hdrs[0].get_slice_orientation(), 'transverse')
    # Add another PAR extension
    nii_img.header.extensions.append(Nifti1Extension('comment', hdr_dump))
    hdrs = exts2pars(nii_img)
    assert_equal(len(hdrs), 2)
    # Test attribute from PARRECHeader
    assert_equal(hdrs[1].get_slice_orientation(), 'transverse')
    # Add null extension, ignored
    nii_img.header.extensions.append(Nifti1Extension('comment', b''))
    # Check all valid inputs
    for source in (nii_img,
                   nii_img.header,
                   nii_img.header.extensions,
                   list(nii_img.header.extensions)):
        hdrs = exts2pars(source)
        assert_equal(len(hdrs), 2)


def test_dualTR():
    expected_TRs = np.asarray([2000., 500.])
    with open(DUAL_TR_PAR, 'rt') as fobj:
        with clear_and_catch_warnings(modules=[parrec], record=True) as wlist:
            simplefilter('always')
            dualTR_hdr = PARRECHeader.from_fileobj(fobj)
        assert_equal(len(wlist), 1)
        assert_array_equal(dualTR_hdr.general_info['repetition_time'],
                           expected_TRs)
        # zoom on 4th dimensions is the first TR (in seconds)
        assert_equal(dualTR_hdr.get_zooms()[3], expected_TRs[0])


def test_ADC_map():
    # test reading an apparent diffusion coefficient map
    with open(ADC_PAR, 'rt') as fobj:

        # two truncation warnings expected because general_info indicates:
        # 1.) multiple directions
        # 2.) multiple b-values
        # but neither of these exist in the post-processed ADC volume.
        with clear_and_catch_warnings(modules=[parrec], record=True) as wlist:
            adc_hdr = PARRECHeader.from_fileobj(fobj, permit_truncated=True)
            assert_equal(len(wlist), 2)

        # general_info indicates it is a diffusion scan, but because it is
        # a post-processed image, the bvals and bvecs aren't available
        bvals, bvecs = adc_hdr.get_bvals_bvecs()
        assert_equal(bvals, None)
        assert_equal(bvecs, None)


def test_alternative_header_field_names():
    # some V4.2 files had variant spellings for some of the fields in the
    # header.  This test reads one such file and verifies that the fields with
    # the alternate spelling were read.
    with ImageOpener(VARIANT_PAR, 'rt') as _fobj:
        HDR_INFO, HDR_DEFS = parse_PAR_header(_fobj)
    assert_equal(HDR_INFO['series_type'], 'Image   MRSERIES')
    assert_equal(HDR_INFO['diffusion_echo_time'], 0.0)
    assert_equal(HDR_INFO['repetition_time'], npa([ 21225.76]))
    assert_equal(HDR_INFO['patient_position'], 'HFS')
