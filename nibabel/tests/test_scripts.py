# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
""" Test scripts

Test running scripts
"""
from __future__ import division, print_function, absolute_import

import sys
import os
from os.path import (dirname, join as pjoin, abspath, splitext, basename,
                     exists)
import csv
from glob import glob

import numpy as np

from ..tmpdirs import InTemporaryDirectory
from ..loadsave import load
from ..orientations import flip_axis, aff2axcodes, inv_ornt_aff

from nose.tools import assert_true, assert_false, assert_equal
from nose import SkipTest

from numpy.testing import assert_almost_equal

from .scriptrunner import ScriptRunner
from .nibabel_data import needs_nibabel_data
from ..testing import assert_dt_equal, assert_re_in
from .test_parrec import (DTI_PAR_BVECS, DTI_PAR_BVALS,
                          EXAMPLE_IMAGES as PARREC_EXAMPLES)
from .test_parrec_data import BALLS, AFF_OFF
from .test_helpers import assert_data_similar


def _proc_stdout(stdout):
    stdout_str = stdout.decode('latin1').strip()
    return stdout_str.replace(os.linesep, '\n')


runner = ScriptRunner(
    script_sdir='bin',
    debug_print_var='NIPY_DEBUG_PRINT',
    output_processor=_proc_stdout)
run_command = runner.run_command


def script_test(func):
    # Decorator to label test as a script_test
    func.script_test = True
    return func
script_test.__test__ = False  # It's not a test

DATA_PATH = abspath(pjoin(dirname(__file__), 'data'))


def check_nib_ls_example4d(opts=[], hdrs_str="", other_str=""):
    # test nib-ls script
    fname = pjoin(DATA_PATH, 'example4d.nii.gz')
    expected_re = (" (int16|[<>]i2) \[128,  96,  24,   2\] "
                   "2.00x2.00x2.20x2000.00  #exts: 2%s sform%s$"
                   % (hdrs_str, other_str))
    cmd = ['nib-ls'] + opts + [fname]
    code, stdout, stderr = run_command(cmd)
    assert_equal(fname, stdout[:len(fname)])
    assert_re_in(expected_re, stdout[len(fname):])


def check_nib_diff_examples(opts=[], hdrs_str="", other_str=""):
    # test nib-diff script
    fnames = [pjoin(DATA_PATH, f)
              for f in ('example4d.nii.gz', 'standard.nii.gz')]
    fnames2 = [pjoin(DATA_PATH, f)
              for f in ('example4d.nii.gz', 'example4d.nii.gz')]
    code, stdout, stderr = run_command(['nib-diff'] + fnames, check_code=False)
    assert_equal(stdout, "Field      /Users/chrischeng/nibabel/nibabel/tests/data/example4d.nii.gz/Users/chrischeng/"
                         "nibabel/nibabel/tests/data/standard.nii.gz"
                                    + "\n" + "regular    b'r'                                         b''              "
                                             "                            " + "\n" + "dim_info   57                    "
                                                                                     "                       0         "
                                                                                     "                                 "
                                                                                     "  " + "\n"
                 "dim        [4, 128, 96, 24, 2, 1, 1, 1]                 [3, 4, 5, 7, 1, 1, 1, 1]                     "
                 + "\n" + "datatype   4                                            2                                   "
                          "         " + "\n" + "bitpix     16                                           8              "
                                               "                              " + "\n" + "pixdim     [-1.0, 2.0, 2.0, "
                                                                                         "2.1999991, 2000.0, 1.0, 1.0,"
                                                                                         " 1.0][1.0, 1.0, 3.0, 2.0, "
                                                                                         "1.0, 1.0, 1.0, 1.0]     " +
                 "\n" + "slice_end  23                                           0                                     "
                        "       " + "\n" + "xyzt_units 10                                           0                  "
                                           "                          " + "\n" + "cal_max    1162.0                    "
                                                                                 "                   0.0               "
                                                                                 "                           " + "\n" +
                 "descrip    b'FSL3.3\\x00 v2.25 NIfTI-1 Single file format'b''                                         "
                 " \n" + "qform_code 1                                            0                                    "
                         "        " + "\n" + "sform_code 1                                            2                "
                                             "                            \n" +"quatern_b  -1.9451068140294884e-26    "
                                                                               "                  0.0                  "
                                                                               "                        " + "\n" +
                 "quatern_c  -0.9967085123062134                          0.0                                          "
                 + "\n" + "quatern_d  -0.0810687392950058                          0.0                                 "
                          "         " + "\n" + "qoffset_x  117.8551025390625                            0.0            "
                                               "                              " + "\n" + "qoffset_y  -35.72294235229492"
                                                                                         "                           0."
                                                                                         "0                            "
                                                                                         "              " + "\n" +
                 "qoffset_z  -7.248798370361328                           0.0                                          "
                 + "\n" + "srow_x     [-2.0, 6.7147157e-19, 9.0810245e-18, 117.8551][1.0, 0.0, 0.0, 0.0]               "
                          "          " + "\n" + "srow_y     [-6.7147157e-19, 1.9737115, -0.35552824, -35.722942][0.0, 3"
                                                ".0, 0.0, 0.0]                         " + "\n" +
                 "srow_z     [8.2554809e-18, 0.32320762, 2.1710818, -7.2487984][0.0, 0.0, 2.0, 0.0]                    "
                 "     " + "\n" + "DATA: These files are different.")

    code, stdout, stderr = run_command(['nib-diff'] + fnames2, check_code=False)
    assert_equal(stdout, "Field      /Users/chrischeng/nibabel/nibabel/tests/data/example4d.nii.gz/Users/chrischeng/nibabel/nibabel/tests/data/example4d.nii.gz"
                         + "\n" + "DATA: These files are identical!")



@script_test
def test_nib_ls():
    yield check_nib_ls_example4d
    yield check_nib_ls_example4d, \
        ['-H', 'dim,bitpix'], " \[  4 128  96  24   2   1   1   1\] 16"
    yield check_nib_ls_example4d, ['-c'], "", " !1030 uniques. Use --all-counts"
    yield check_nib_ls_example4d, ['-c', '--all-counts'], "", " 2:3 3:2 4:1 5:1.*"
    # both stats and counts
    yield check_nib_ls_example4d, \
        ['-c', '-s', '--all-counts'], "", " \[229725\] \[2, 1.2e\+03\] 2:3 3:2 4:1 5:1.*"
    # and must not error out if we allow for zeros
    yield check_nib_ls_example4d, \
        ['-c', '-s', '-z', '--all-counts'], "", " \[589824\] \[0, 1.2e\+03\] 0:360099 2:3 3:2 4:1 5:1.*"


@script_test
def test_nib_ls_multiple():
    # verify that correctly lists/formats for multiple files
    fnames = [
        pjoin(DATA_PATH, f)
        for f in ('example4d.nii.gz', 'example_nifti2.nii.gz',
                  'small.mnc', 'nifti2.hdr')
    ]
    code, stdout, stderr = run_command(['nib-ls'] + fnames)
    stdout_lines = stdout.split('\n')
    assert_equal(len(stdout_lines), 4)
    try:
        load(pjoin(DATA_PATH, 'small.mnc'))
    except:
        raise SkipTest("For the other tests should be able to load MINC files")

    # they should be indented correctly.  Since all files are int type -
    ln = max(len(f) for f in fnames)
    i_str = ' i' if sys.byteorder == 'little' else ' <i'
    assert_equal([l[ln:ln + len(i_str)] for l in stdout_lines], [i_str] * 4,
          msg="Type sub-string didn't start with '%s'. "
              "Full output was: %s" % (i_str, stdout_lines))
    # and if disregard type indicator which might vary
    assert_equal(
        [l[l.index('['):] for l in stdout_lines],
        [
            '[128,  96,  24,   2] 2.00x2.00x2.20x2000.00  #exts: 2 sform',
            '[ 32,  20,  12,   2] 2.00x2.00x2.20x2000.00  #exts: 2 sform',
            '[ 18,  28,  29]      9.00x8.00x7.00',
            '[ 91, 109,  91]      2.00x2.00x2.00'
        ]
    )

    # Now run with -s for stats
    code, stdout, stderr = run_command(['nib-ls', '-s'] + fnames)
    stdout_lines = stdout.split('\n')
    assert_equal(len(stdout_lines), 4)
    assert_equal(
        [l[l.index('['):] for l in stdout_lines],
        [
            '[128,  96,  24,   2] 2.00x2.00x2.20x2000.00  #exts: 2 sform [229725] [2, 1.2e+03]',
            '[ 32,  20,  12,   2] 2.00x2.00x2.20x2000.00  #exts: 2 sform [15360]  [46, 7.6e+02]',
            '[ 18,  28,  29]      9.00x8.00x7.00                         [14616]  [0.12, 93]',
            '[ 91, 109,  91]      2.00x2.00x2.00                          !error'
        ]
    )


@script_test
def test_nib_diff():
    yield check_nib_diff_examples


@script_test
def test_nib_nifti_dx():
    # Test nib-nifti-dx script
    clean_hdr = pjoin(DATA_PATH, 'nifti1.hdr')
    cmd = ['nib-nifti-dx', clean_hdr]
    code, stdout, stderr = run_command(cmd)
    assert_equal(stdout.strip(), 'Header for "%s" is clean' % clean_hdr)
    dirty_hdr = pjoin(DATA_PATH, 'analyze.hdr')
    cmd = ['nib-nifti-dx', dirty_hdr]
    code, stdout, stderr = run_command(cmd)
    expected = """Picky header check output for "%s"

pixdim[0] (qfac) should be 1 (default) or -1
magic string "" is not valid
sform_code 11776 not valid""" % (dirty_hdr,)
    # Split strings to remove line endings
    assert_equal(stdout, expected)


def vox_size(affine):
    return np.sqrt(np.sum(affine[:3, :3] ** 2, axis=0))


def check_conversion(cmd, pr_data, out_fname):
    run_command(cmd)
    img = load(out_fname)
    # Check orientations always LAS
    assert_equal(aff2axcodes(img.affine), tuple('LAS'))
    data = img.get_data()
    assert_true(np.allclose(data, pr_data))
    assert_true(np.allclose(img.header['cal_min'], data.min()))
    assert_true(np.allclose(img.header['cal_max'], data.max()))
    del img, data  # for windows to be able to later delete the file
    # Check minmax options
    run_command(cmd + ['--minmax', '1', '2'])
    img = load(out_fname)
    data = img.get_data()
    assert_true(np.allclose(data, pr_data))
    assert_true(np.allclose(img.header['cal_min'], 1))
    assert_true(np.allclose(img.header['cal_max'], 2))
    del img, data  # for windows
    run_command(cmd + ['--minmax', 'parse', '2'])
    img = load(out_fname)
    data = img.get_data()
    assert_true(np.allclose(data, pr_data))
    assert_true(np.allclose(img.header['cal_min'], data.min()))
    assert_true(np.allclose(img.header['cal_max'], 2))
    del img, data  # for windows
    run_command(cmd + ['--minmax', '1', 'parse'])
    img = load(out_fname)
    data = img.get_data()
    assert_true(np.allclose(data, pr_data))
    assert_true(np.allclose(img.header['cal_min'], 1))
    assert_true(np.allclose(img.header['cal_max'], data.max()))
    del img, data


@script_test
def test_parrec2nii():
    # Test parrec2nii script
    cmd = ['parrec2nii', '--help']
    code, stdout, stderr = run_command(cmd)
    assert_true(stdout.startswith('Usage'))
    with InTemporaryDirectory():
        for eg_dict in PARREC_EXAMPLES:
            fname = eg_dict['fname']
            run_command(['parrec2nii', fname])
            out_froot = splitext(basename(fname))[0] + '.nii'
            img = load(out_froot)
            assert_equal(img.shape, eg_dict['shape'])
            assert_dt_equal(img.get_data_dtype(), eg_dict['dtype'])
            # Check against values from Philips converted nifti image
            data = img.get_data()
            assert_data_similar(data, eg_dict)
            assert_almost_equal(img.header.get_zooms(), eg_dict['zooms'])
            # Standard save does not save extensions
            assert_equal(len(img.header.extensions), 0)
            # Delete previous img, data to make Windows happier
            del img, data
            # Does not overwrite unless option given
            code, stdout, stderr = run_command(
                ['parrec2nii', fname], check_code=False)
            assert_equal(code, 1)
            # Default scaling is dv
            pr_img = load(fname)
            flipped_data = flip_axis(pr_img.get_data(), 1)
            base_cmd = ['parrec2nii', '--overwrite', fname]
            check_conversion(base_cmd, flipped_data, out_froot)
            check_conversion(base_cmd + ['--scaling=dv'],
                             flipped_data,
                             out_froot)
            # fp
            pr_img = load(fname, scaling='fp')
            flipped_data = flip_axis(pr_img.get_data(), 1)
            check_conversion(base_cmd + ['--scaling=fp'],
                             flipped_data,
                             out_froot)
            # no scaling
            unscaled_flipped = flip_axis(pr_img.dataobj.get_unscaled(), 1)
            check_conversion(base_cmd + ['--scaling=off'],
                             unscaled_flipped,
                             out_froot)
            # Save extensions
            run_command(base_cmd + ['--store-header'])
            img = load(out_froot)
            assert_equal(len(img.header.extensions), 1)
            del img  # To help windows delete the file


@script_test
@needs_nibabel_data('nitest-balls1')
def test_parrec2nii_with_data():
    # Use nibabel-data to test conversion
    # Premultiplier to relate our affines to Philips conversion
    LAS2LPS = inv_ornt_aff([[0, 1], [1, -1], [2, 1]], (80, 80, 10))
    with InTemporaryDirectory():
        for par in glob(pjoin(BALLS, 'PARREC', '*.PAR')):
            par_root, ext = splitext(basename(par))
            # NA.PAR appears to be a localizer, with three slices in each of
            # the three orientations: sagittal; coronal, transverse
            if par_root == 'NA':
                continue
            # Do conversion
            run_command(['parrec2nii', par])
            conved_img = load(par_root + '.nii')
            # Confirm parrec2nii conversions are LAS
            assert_equal(aff2axcodes(conved_img.affine), tuple('LAS'))
            # Shape same whether LPS or LAS
            assert_equal(conved_img.shape[:3], (80, 80, 10))
            # Test against original converted NIfTI
            nifti_fname = pjoin(BALLS, 'NIFTI', par_root + '.nii.gz')
            if exists(nifti_fname):
                philips_img = load(nifti_fname)
                # Confirm Philips converted image always LPS
                assert_equal(aff2axcodes(philips_img.affine), tuple('LPS'))
                # Equivalent to Philips LPS affine
                equiv_affine = conved_img.affine.dot(LAS2LPS)
                assert_almost_equal(philips_img.affine[:3, :3],
                                    equiv_affine[:3, :3], 3)
                # The translation part is always off by the same ammout
                aff_off = equiv_affine[:3, 3] - philips_img.affine[:3, 3]
                assert_almost_equal(aff_off, AFF_OFF, 3)
                # The difference is max in the order of 0.5 voxel
                vox_sizes = vox_size(philips_img.affine)
                assert_true(np.all(np.abs(aff_off / vox_sizes) <= 0.501))
                # The data is very close, unless it's the fieldmap
                if par_root != 'fieldmap':
                    conved_data_lps = flip_axis(conved_img.dataobj, 1)
                    assert_true(np.allclose(conved_data_lps,
                                            philips_img.dataobj))
    with InTemporaryDirectory():
        # Test some options
        dti_par = pjoin(BALLS, 'PARREC', 'DTI.PAR')
        run_command(['parrec2nii', dti_par])
        assert_true(exists('DTI.nii'))
        assert_false(exists('DTI.bvals'))
        assert_false(exists('DTI.bvecs'))
        # Does not overwrite unless option given
        code, stdout, stderr = run_command(['parrec2nii', dti_par],
                                           check_code=False)
        assert_equal(code, 1)
        # Writes bvals, bvecs files if asked
        run_command(['parrec2nii', '--overwrite', '--keep-trace',
                     '--bvs', dti_par])
        bvecs_trace = np.loadtxt('DTI.bvecs').T
        bvals_trace = np.loadtxt('DTI.bvals')
        assert_almost_equal(bvals_trace, DTI_PAR_BVALS)
        img = load('DTI.nii')
        data = img.get_data().copy()
        del img
        # Bvecs in header, transposed from PSL to LPS
        bvecs_LPS = DTI_PAR_BVECS[:, [2, 0, 1]]
        # Adjust for output flip of Y axis in data and bvecs
        bvecs_LAS = bvecs_LPS * [1, -1, 1]
        assert_almost_equal(np.loadtxt('DTI.bvecs'), bvecs_LAS.T)
        # Dwell time
        assert_false(exists('DTI.dwell_time'))
        # Need field strength if requesting dwell time
        code, _, _, = run_command(
            ['parrec2nii', '--overwrite', '--dwell-time', dti_par],
            check_code=False)
        assert_equal(code, 1)
        run_command(
            ['parrec2nii', '--overwrite', '--dwell-time',
             '--field-strength', '3', dti_par])
        exp_dwell = (26 * 9.087) / (42.576 * 3.4 * 3 * 28)
        with open('DTI.dwell_time', 'rt') as fobj:
            contents = fobj.read().strip()
        assert_almost_equal(float(contents), exp_dwell)
        # ensure trace is removed by default
        run_command(['parrec2nii', '--overwrite', '--bvs', dti_par])
        assert_true(exists('DTI.bvals'))
        assert_true(exists('DTI.bvecs'))
        img = load('DTI.nii')
        bvecs_notrace = np.loadtxt('DTI.bvecs').T
        bvals_notrace = np.loadtxt('DTI.bvals')
        data_notrace = img.get_data().copy()
        assert_equal(data_notrace.shape[-1], len(bvecs_notrace))
        del img
        # ensure correct volume was removed
        good_mask = np.logical_or((bvecs_trace != 0).any(axis=1),
                                  bvals_trace == 0)
        assert_almost_equal(data_notrace, data[..., good_mask])
        assert_almost_equal(bvals_notrace, np.array(DTI_PAR_BVALS)[good_mask])
        assert_almost_equal(bvecs_notrace, bvecs_LAS[good_mask])
        # test --strict-sort
        run_command(['parrec2nii', '--overwrite', '--keep-trace',
                     '--bvs', '--strict-sort', dti_par])
        # strict-sort: bvals should be in ascending order
        assert_almost_equal(np.loadtxt('DTI.bvals'), np.sort(DTI_PAR_BVALS))
        img = load('DTI.nii')
        data_sorted = img.get_data().copy()
        assert_almost_equal(data[..., np.argsort(DTI_PAR_BVALS)], data_sorted)
        del img

        # Writes .ordering.csv if requested
        run_command(['parrec2nii', '--overwrite', '--volume-info', dti_par])
        assert_true(exists('DTI.ordering.csv'))
        with open('DTI.ordering.csv', 'r') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=',')
            csv_keys = next(csvreader)  # header row
            nlines = 0  # count number of non-header rows
            for line in csvreader:
                nlines += 1

        assert_equal(sorted(csv_keys), ['diffusion b value number',
                                        'gradient orientation number'])
        assert_equal(nlines, 8)  # 8 volumes present in DTI.PAR
