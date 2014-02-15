# emacs: -*- mode: python-mode; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NiBabel package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Humble attempt to read images in PAR/REC format.

This is yet another MRI image format generated by Phillips
scanner. It is an ASCII header (PAR) plus a binary blob (REC).

This implementation aims to read version 4.2 of this format. Other versions
could probably be supported, but the author is lacking samples of them.
"""

import warnings
import numpy as np
import copy

from .spatialimages import SpatialImage, Header
from .eulerangles import euler2mat
from .volumeutils import Recoder, array_from_file, apply_read_scaling
from .arrayproxy import ArrayProxy

# PAR header versions we claim to understand
supported_versions = ['V4.2']

# assign props to PAR header entries
# values are: (shortname[, dtype[, shape]])
_hdr_key_dict = {
    'Patient name': ('patient_name',),
    'Examination name': ('exam_name',),
    'Protocol name': ('protocol_name',),
    'Examination date/time': ('exam_date',),
    'Series Type': ('series_type',),
    'Acquisition nr': ('acq_nr', int),
    'Reconstruction nr': ('recon_nr', int),
    'Scan Duration [sec]': ('scan_duration', float),
    'Max. number of cardiac phases': ('max_cardiac_phases', int),
    'Max. number of echoes': ('max_echoes', int),
    'Max. number of slices/locations': ('max_slices', int),
    'Max. number of dynamics': ('max_dynamics', int),
    'Max. number of mixes': ('max_mixes', int),
    'Patient position': ('patient_position',),
    'Preparation direction': ('prep_direction',),
    'Technique': ('tech',),
    'Scan resolution  (x, y)': ('scan_resolution', int, (2,)),
    'Scan mode': ('san_mode',),
    'Repetition time [ms]': ('repetition_time', float),
    'FOV (ap,fh,rl) [mm]': ('fov', float, (3,)),
    'Water Fat shift [pixels]': ('water_fat_shift', float),
    'Angulation midslice(ap,fh,rl)[degr]': ('angulation', float, (3,)),
    'Off Centre midslice(ap,fh,rl) [mm]': ('off_center', float, (3,)),
    'Flow compensation <0=no 1=yes> ?': ('flow_compensation', int),
    'Presaturation     <0=no 1=yes> ?': ('presaturation', int),
    'Phase encoding velocity [cm/sec]': ('phase_enc_velocity', float, (3,)),
    'MTC               <0=no 1=yes> ?': ('mtc', int),
    'SPIR              <0=no 1=yes> ?': ('spir', int),
    'EPI factor        <0,1=no EPI>': ('epi_factor', int),
    'Dynamic scan      <0=no 1=yes> ?': ('dyn_scan', int),
    'Diffusion         <0=no 1=yes> ?': ('diffusion', int),
    'Diffusion echo time [ms]': ('diffusion_echo_time', float),
    'Max. number of diffusion values': ('max_diffusion_values', int),
    'Max. number of gradient orients': ('max_gradient_orient', int),
    'Number of label types   <0=no ASL>': ('nr_label_types', int),
    }

# header items order per image definition line
image_def_dtd = [
    ('slice number', int),
    ('echo number', int,),
    ('dynamic scan number', int,),
    ('cardiac phase number', int,),
    ('image_type_mr', int,),
    ('scanning sequence', int,),
    ('index in REC file', int,),
    ('image pixel size', int,),
    ('scan percentage', int,),
    ('recon resolution', int, (2,)),
    ('rescale intercept', float),
    ('rescale slope', float),
    ('scale slope', float),
    ('window center', int,),
    ('window width', int,),
    ('image angulation', float, (3,)),
    ('image offcentre', float, (3,)),
    ('slice thickness', float),
    ('slice gap', float),
    ('image_display_orientation', int,),
    ('slice orientation', int,),
    ('fmri_status_indication', int,),
    ('image_type_ed_es', int,),
    ('pixel spacing', float, (2,)),
    ('echo_time', float),
    ('dyn_scan_begin_time', float),
    ('trigger_time', float),
    ('diffusion_b_factor', float),
    ('number of averages', int,),
    ('image_flip_angle', float),
    ('cardiac frequency', int,),
    ('minimum RR-interval', int,),
    ('maximum RR-interval', int,), 
    ('TURBO factor', int,),
    ('Inversion delay', float),
    ('diffusion b value number', int,),    # (imagekey!)
    ('gradient orientation number', int,), # (imagekey!)
    ('contrast type', 'S30'),              # XXX might be too short?
    ('diffusion anisotropy type', 'S30'),  # XXX might be too short?
    ('diffusion', float, (3,)),
    ('label type', int,),                  # (imagekey!)
    ]
image_def_dtype = np.dtype(image_def_dtd)

# slice orientation codes
slice_orientation_codes = Recoder((# code, label
    (1, 'transversal'),
    (2, 'sagital'),
    (3, 'coronal')), fields=('code', 'label'))


class PARRECError(Exception):
    """Exception for PAR/REC format related problems.

    To be raised whenever PAR/REC is not happy, or we are not happy with
    PAR/REC.
    """
    pass


def parse_PAR_header(fobj):
    """Parse a PAR header and aggregate all information into useful containers.

    Parameters
    ----------
    fobj : file-object
      The PAR header file object.

    Returns
    -------
    (dict, array)
      The dictionary contains all "General Information" from the header file,
      while the (structured) has the properties of all image definitions in the
      header
    """
    # containers for relevant header lines
    general_info = {}
    image_info = []
    version = None

    # single pass through the header
    for line in fobj:
        # no junk
        line = line.strip()
        if line.startswith('#'):
            # try to get the header version
            if line.count('image export tool'):
                version = line.split()[-1]
                if not version in supported_versions:
                    warnings.warn(
                          "PAR/REC version '%s' is currently not "
                          "supported -- making an attempt to read "
                          "nevertheless. Please email the NiBabel "
                          "mailing list, if you are interested in "
                          "adding support for this version."
                          % version)
            else:
                # just a comment
                continue
        elif line.startswith('.'):
            # read 'general information' and store in a dict
            first_colon = line[1:].find(':') + 1
            key = line[1:first_colon].strip()
            value = line[first_colon + 1:].strip()
            # get props for this hdr field
            props = _hdr_key_dict[key]
            # turn values into meaningful dtype
            if len(props) == 2:
                # only dtype spec and no shape
                value = props[1](value)
            elif len(props) == 3:
                # array with dtype and shape
                value = np.fromstring(value, props[1], sep=' ')
                value.shape = props[2]
            general_info[props[0]] = value
        elif line:
            # anything else is an image definition: store for later
            # processing
            image_info.append(line)

    # postproc image def props
    # create an array for all image defs
    image_defs = np.zeros(len(image_info), dtype=image_def_dtype)

    # for every image definition
    for i, line in enumerate(image_info):
        items = line.split()
        item_counter = 0
        # for all image properties we know about
        for props in image_def_dtd:
            if np.issubdtype(image_defs[props[0]].dtype, str):
                # simple string
                image_defs[props[0]][i] = items[item_counter]
                item_counter += 1
            elif len(props) == 2:
                # prop with numerical dtype
                image_defs[props[0]][i] = props[1](items[item_counter])
                item_counter += 1
            elif len(props) == 3:
                # array prop with dtype
                nelements = np.prod(props[2])
                # get as many elements as necessary
                itms = items[item_counter:item_counter + nelements]
                # convert to array with dtype
                value = np.fromstring(" ".join(itms), props[1], sep=' ')
                # store
                image_defs[props[0]][i] = value
                item_counter += nelements

    return general_info, image_defs


class PARRECHeader(Header):
    """PAR/REC header"""
    def __init__(self, info, image_defs, default_scaling='dv'):
        """
        Parameters
        ----------
        info : dict
          "General information" from the PAR file (as returned by
          `parse_PAR_header()`).
        image_defs : array
          Structured array with image definitions from the PAR file (as returned
          by `parse_PAR_header()`).
        default_scaling : {'dv', 'fp'}
          Default scaling method to use for :meth:`get_slope_inter`` - see
          :meth:`get_data_scaling` for detail
        """
        self.general_info = info
        self.image_defs = image_defs
        self._slice_orientation = None
        self.default_scaling = default_scaling
        # charge with basic properties to be able to use base class
        # functionality
        # dtype
        dtype = np.typeDict[
                    'int'
                    + str(self._get_unique_image_prop('image pixel size')[0])]
        Header.__init__(self,
                        data_dtype=dtype,
                        shape=self.get_data_shape_in_file(),
                        zooms=self._get_zooms()
                       )


    @classmethod
    def from_header(klass, header=None):
        if header is None:
            raise PARRECError('Cannot create PARRECHeader from air.')
        if type(header) == klass:
            return header.copy()
        raise PARRECError('Cannot create PARREC header from non-PARREC header.')


    @classmethod
    def from_fileobj(klass, fileobj):
        info, image_defs = parse_PAR_header(fileobj)
        return klass(info, image_defs)


    def copy(self):
        return PARRECHeader(
                copy.deepcopy(self.general_info),
                self.image_defs.copy())


    def _get_unique_image_prop(self, name):
        """Scan all image definitions and return the unique value of a property.

        If the requested property is an array this method behave _not_ like
        `np.unique`. It will return the unique combination of all array elements
        for any image definition, and _not_ the unique element values.

        Raises
        ------
        If there is more than a single unique value a `PARRECError` is raised.
        """
        prop = self.image_defs[name]
        if len(prop.shape) > 1:
            uprops = [np.unique(prop[i]) for i in range(len(prop.shape))]
        else:
            uprops = [np.unique(prop)]
        if not np.prod([len(uprop) for uprop in uprops]) == 1:
            raise PARRECError('Varying %s in image sequence (%s). This is not '
                              'suppported.' % (name, uprops))
        else:
            return np.array([uprop[0] for uprop in uprops])


    def get_voxel_size(self):
        """Returns the spatial extent of a voxel.

        Returns
        -------
        Array
        """
        # slice orientation for the whole image series
        slice_thickness = self._get_unique_image_prop('slice thickness')[0]
        voxsize_inplane = self._get_unique_image_prop('pixel spacing')
        voxsize = np.array((voxsize_inplane[0],
                            voxsize_inplane[1],
                            slice_thickness))
        return voxsize

    def get_data_offset(self):
        """ PAR header always has 0 data offset (into REC file) """
        return 0

    def get_ndim(self):
        """Return the number of dimensions of the image data."""
        if self.general_info['max_dynamics'] > 1 \
           or self.general_info['max_gradient_orient'] > 1:
            return 4
        else:
            return 3


    def _get_zooms(self):
        """Compute image zooms from header data.

        Spatial axis are first three.
        """
        # slice orientation for the whole image series
        slice_gap = self._get_unique_image_prop('slice gap')[0]
        # scaling per image axis
        zooms = np.ones(self.get_ndim())
        # spatial axes correspond to voxelsize + inter slice gap
        # voxel size (inplaneX, inplaneY, slices)
        zooms[:3] = self.get_voxel_size()
        zooms[2] += slice_gap
        # time axis?
        if len(zooms) > 3  and self.general_info['max_dynamics'] > 1:
            # DTI also has 4D
            # Convert time from milliseconds to seconds
            zooms[3] = self.general_info['repetition_time'] / 1000.
        return zooms


    def get_affine(self, origin='scanner'):
        """Compute affine transformation into scanner space.

        The method only considers global rotation and offset settings in the
        header and ignore potentially deviating information in the image
        definitions.

        Parameters
        ----------
        origin : {'scanner', 'fov'}
          Transformation origin. By default the transformation is computed
          relative to the scanner's iso center. If 'fov' is requested
          the transformation origin will be the center of the field of view
          instead.

        Returns
        -------
        array
          4x4 array, with axis order corresponding to (x,y,z) or (lr, pa, fh).
        """
        # hdr has deg, we need radian
        # order is [ap, fh, rl]
        ang_rad = self.general_info['angulation'] * np.pi / 180.0
        # need to rotate back from what was given in the file
        ang_rad *= -1

        # R2AGUI approach is this, but it comes with remarks ;-)
        # % trying to incorporate AP FH RL rotation angles: determined using some 
        # % common sense, Chris Rordon's help + source code and trial and error, 
        # % this is considered EXPERIMENTAL!
        rot_rl = np.mat(
                [[1.0, 0.0, 0.0],
                 [0.0, np.cos(ang_rad[2]), -np.sin(ang_rad[2])],
                 [0.0, np.sin(ang_rad[2]), np.cos(ang_rad[2])]]
                )
        rot_ap = np.mat(
                [[np.cos(ang_rad[0]), 0.0, np.sin(ang_rad[0])],
                 [0.0, 1.0, 0.0],
                 [-np.sin(ang_rad[0]), 0.0, np.cos(ang_rad[0])]]
                )
        rot_fh = np.mat(
                [[np.cos(ang_rad[1]), -np.sin(ang_rad[1]), 0.0],
                 [np.sin(ang_rad[1]), np.cos(ang_rad[1]), 0.0],
                 [0.0, 0.0, 1.0]]
                )
        rot_r2agui = rot_rl * rot_ap * rot_fh
        # NiBabel way of doing it
        # order is [ap, fh, rl]
        #           x   y   z
        #           0   1   2
        rot_nibabel = euler2mat(ang_rad[1], ang_rad[0], ang_rad[2])

        # XXX for now put some safety net, until we have recorded proper
        # test data with oblique orientations and different readout directions
        # to verify the order of arguments of euler2mat
        assert(np.all(rot_r2agui == rot_nibabel))
        rot = rot_nibabel

        # FOV (always in ap, fh, rl)
        fov = self.general_info['fov']
        # voxel size always (inplaneX, inplaneY, slicethickness (without gap))
        voxsize = self.get_voxel_size()

        slice_orientation = self.get_slice_orientation()
        if slice_orientation == 'sagital':
            # inplane: AP, FH   slices: RL
            recfg_data_axis = np.mat([[  0,  0,  1],
                                      [ -1,  0,  0],
                                      [  0, -1,  0]])
            # fov is already like the data
            fov = fov
        elif slice_orientation == 'transversal':
            # inplane: RL, AP   slices: FH
            recfg_data_axis = np.mat([[ -1,  0,  0],
                                      [  0, -1,  0],
                                      [  0,  0,  1]])
            # fov is already like the data
            fov = fov[[2,0,1]]
        elif slice_orientation == 'coronal':
            # inplane: RL, FH   slices: AP
            recfg_data_axis = np.mat([[ -1,  0,  0],
                                      [  0,  0, -1],
                                      [  0, -1,  0]])
            # fov is already like the data
            fov = fov[[2,1,0]]
        else:
            raise PARRECError("Unknown slice orientation (%s)."
                              % slice_orientation)

        rot = rot * recfg_data_axis

        # ijk origin should be: Anterior, Right, Foot
        # qform should point to the center of the voxel
        fov_center_offset = self.get_voxel_size() / 2 - fov / 2

        # need to rotate this offset into scanner space
        fov_center_offset = np.dot(rot, fov_center_offset)

        # get the scaling by voxelsize and slice thickness (incl. gap)
        scaled = rot * np.mat(np.diag(self.get_zooms()[:3]))

        # compose the affine
        aff = np.eye(4)
        aff[:3,:3] = scaled
        # offset
        aff[:3,3] = fov_center_offset
        if origin == 'fov':
            pass
        elif origin == 'scanner':
            # offset to scanner's iso center (always in ap, fh, rl)
            # -- turn into rl, ap, fh and then lr, pa, fh
            iso_offset = self.general_info['off_center'][[2,0,1]] * [-1,-1,0]
            aff[:3,3] += iso_offset
        return aff


    def get_data_shape_in_file(self):
        """Return the shape of the binary blob in the REC file.

        Returns
        -------
        tuple
          (inplaneX, inplaneY, nslices, ndynamics/ndirections)
        """
        # e.g. number of volumes
        ndynamics = len(np.unique(self.image_defs['dynamic scan number']))
        # DTI volumes (b-values-1 x directions)
        # there is some awkward exception to this rule for b-values > 2
        # XXX need to get test image...
        ndtivolumes = (self.general_info['max_diffusion_values'] - 1) \
                        * self.general_info['max_gradient_orient']
        nslices = len(np.unique(self.image_defs['slice number']))
        if not nslices == self.general_info['max_slices']:
            raise PARRECError("Header inconsistency: Found %i slices, "
                              "but header claims to have %i."
                              % (nslices, self.general_info['max_slices']))

        inplane_shape = tuple(self._get_unique_image_prop('recon resolution'))

        # there should not be both: multiple dynamics and DTI
        if ndynamics > 1:
            return inplane_shape + (nslices, ndynamics)
        elif ndtivolumes > 1:
            return inplane_shape + (nslices, ndtivolumes)
        else:
            return tuple(inplane_shape) + (nslices,)


    def get_data_scaling(self, method="dv"):
        """Returns scaling slope and intercept.

        Parameters
        ----------
        method : {'fp', 'dv'}
          Scaling settings to be reported -- see notes below.

        Notes
        -----
        The PAR header contains two different scaling settings: 'dv' (value on
        console) and 'fp' (floating point value). Here is how they are defined:

        PV: value in REC
        RS: rescale slope
        RI: rescale intercept
        SS: scale slope

        DV = PV * RS + RI
        FP = DV / (RS * SS)
        """
        # XXX: FP tends to become HUGE, DV seems to be more reasonable -> figure
        #      out which one means what

        # although the is a per-image scaling in the header, it looks like
        # there is just one unique factor and intercept per whole image series
        scale_slope = self._get_unique_image_prop('scale slope')
        rescale_slope = self._get_unique_image_prop('rescale slope')
        rescale_intercept = self._get_unique_image_prop('rescale intercept')

        if method == 'dv':
            slope = rescale_slope
            intercept = rescale_intercept
        elif method == 'fp':
            # actual slopes per definition above
            slope = 1.0 / scale_slope
            # actual intercept per definition above
            intercept = rescale_intercept / (rescale_slope * scale_slope)
        else:
            raise ValueError("Unknown scling method '%s'." % method)
        return (slope, intercept)

    def get_slope_inter(self):
        """ Utility method to get default slope, intercept scaling
        """
        return tuple(
            np.asscalar(v)
            for v in self.get_data_scaling(method=self.default_scaling))

    def get_slice_orientation(self):
        """Returns the slice orientation label.

        Returns
        -------
        {'transversal', 'sagital', 'coronal'}
        """
        if self._slice_orientation is None:
            self._slice_orientation = \
                slice_orientation_codes.label[
                    self._get_unique_image_prop('slice orientation')[0]]
        return self._slice_orientation


    def raw_data_from_fileobj(self, fileobj):
        ''' Read unscaled data array from `fileobj`

        Array axes correspond to x,y,z,t.

        Parameters
        ----------
        fileobj : file-like
           Must be open, and implement ``read`` and ``seek`` methods

        Returns
        -------
        arr : ndarray
           unscaled data array
        '''
        dtype = self.get_data_dtype()
        shape = self.get_data_shape()
        offset = self.get_data_offset()
        return array_from_file(shape, dtype, fileobj, offset)

    def data_from_fileobj(self, fileobj):
        ''' Read scaled data array from `fileobj`

        Use this routine to get the scaled image data from an image file
        `fileobj`, given a header `self`.  "Scaled" means, with any header
        scaling factors applied to the raw data in the file.  Use
        `raw_data_from_fileobj` to get the raw data.

        Parameters
        ----------
        fileobj : file-like
           Must be open, and implement ``read`` and ``seek`` methods

        Returns
        -------
        arr : ndarray
           scaled data array
        '''
        # read unscaled data
        data = self.raw_data_from_fileobj(fileobj)
        # get scalings from header.  Value of None means not present in header
        slope, inter = self.get_slope_inter()
        slope = 1.0 if slope is None else slope
        inter = 0.0 if inter is None else inter
        # Upcast as necessary for big slopes, intercepts
        return apply_read_scaling(data, slope, inter)


class PARRECImage(SpatialImage):
    """PAR/REC image"""
    header_class = PARRECHeader
    files_types = (('image', '.rec'), ('header', '.par'))

    ImageArrayProxy = ArrayProxy

    @classmethod
    def from_file_map(klass, file_map):
        with file_map['header'].get_prepare_fileobj('rt') as hdr_fobj:
            hdr = PARRECHeader.from_fileobj(hdr_fobj)
        rec_fobj = file_map['image'].get_prepare_fileobj()
        data = klass.ImageArrayProxy(rec_fobj, hdr)
        return klass(data,
                     hdr.get_affine(),
                     header=hdr,
                     extra=None,
                     file_map=file_map)


load = PARRECImage.load
