import re

import jpegtran.lib as lib


EXIF_ROT_MAP = {
    90: {1: 8, 8: 3, 3: 6, 6: 1, 2: 7, 7: 4, 4: 5, 5: 2},
    180: {1: 3, 3: 1, 2: 4, 4: 2, 5: 7, 7: 5, 6: 8, 8: 6},
    270: {1: 6, 6: 3, 3: 8, 8: 1, 2: 5, 5: 4, 4: 7, 7: 2},
}
EXIF_FLIP_MAP = {
    'horizontal': {1: 2, 2: 1, 3: 4, 4: 3, 5: 6, 6: 5, 7: 8, 8: 7},
    'vertical': {1: 4, 4: 1, 2: 3, 3: 2, 5: 8, 8: 5, 6: 7, 7: 6},
}
EXIF_TRANSPOSE_MAP = {1: 5, 5: 1, 2: 6, 6: 2, 3: 7, 7: 3, 4: 8, 8: 4}
EXIF_TRANVERSE_MAP = {1: 7, 7: 1, 2: 8, 8: 2, 3: 5, 5: 3, 4: 6, 6: 4}

class JPEGImage(object):
    def __init__(self, fname=None, blob=None):
        """ Initialize the image with either a filename or a string or
        bytearray containing the JPEG image data.

        :param fname:   Filename of JPEG file
        :type fname:    str
        :param blob:    JPEG image data
        :type blob:     str/bytearray

        """
        if (not fname and not blob) or (fname and blob):
            raise Exception("Must initialize with either fname or blob.")
        if fname is not None:
            with open(fname, 'rb') as fp:
                self.data = bytearray(fp.read())
        elif blob is not None:
            self.data = bytearray(blob)

    @property
    def width(self):
        """ Width of the image in pixels. """
        return lib.Transformation(self.data).get_dimensions()[0]

    @property
    def height(self):
        """ Height of the image in pixels. """
        return lib.Transformation(self.data).get_dimensions()[1]

    @property
    def exif_thumbnail(self):
        """ EXIF thumbnail.

        :return:  EXIF thumbnail in JPEG format
        :rtype:   str

        """
        try:
            return JPEGImage(blob=lib.Exif(self.data).thumbnail)
        except lib.ExifException:
            return None

    @exif_thumbnail.setter
    def exif_thumbnail(self, image):
        if isinstance(image, JPEGImage):
            data = image.data
        elif isinstance(image, bytes):
            data = bytearray(image)
        else:
            data = image
        if not self.exif_thumbnail:
            raise ValueError("No pre-existing thumbnail found, cannot set.")
        lib.Exif(self.data).thumbnail = data

    @property
    def exif_orientation(self):
        """ Exif orientation value as a number between 1 and 8.

        Property is read/write
        """
        try:
            return lib.Exif(self.data).orientation
        except lib.ExifException:
            return None

    @exif_orientation.setter
    def exif_orientation(self, value):
        if not 0 < value < 9:
            raise ValueError("Orientation value must be between 1 and 8")
        lib.Exif(self.data).orientation = value

    def exif_autotransform(self):
        """ Automatically transform the image according to its EXIF orientation
        tag.

        :return:  transformed image
        :rtype:   jpegtran.JPEGImage

        """
        orient = self.exif_orientation
        if orient is None:
            raise Exception("Could not find EXIF orientation")
        elif orient == 1:
            return self
        elif orient == 2:
            return self.flip('horizontal', with_exif=True)
        elif orient == 3:
            return self.rotate(180, with_exif=True)
        elif orient == 4:
            return self.flip('vertical', with_exif=True)
        elif orient == 5:
            return self.transpose(with_exif=True)
        elif orient == 6:
            return self.rotate(90, with_exif=True)
        elif orient == 7:
            return self.transverse(with_exif=True)
        elif orient == 8:
            return self.rotate(270, with_exif=True)

    def rotate(self, angle, with_exif=False):
        """ Rotate the image.

        :param angle:   rotation angle
        :return:        rotated image

        """
        if angle not in (90, 180, 270):
            raise ValueError("Angle must be 90, 180 or 270.")
        
        img = JPEGImage(blob=lib.Transformation(self.data).rotate(angle))
        if with_exif:
            img.exif_orientation = EXIF_ROT_MAP[angle][img.exif_orientation or 1]
        img._update_thumbnail()
        return img

    def flip(self, direction, with_exif=False):
        """ Flip the image in horizontal or vertical direction.

        :param direction: Flipping direction
        :type direction:  'vertical' or 'horizontal'
        :return:        flipped image
        :rtype:         jpegtran.JPEGImage

        """
        if direction not in ('horizontal', 'vertical'):
            raise ValueError("Direction must be either 'vertical' or "
                             "'horizontal'")
        new = JPEGImage(blob=lib.Transformation(self.data).flip(direction))
        if with_exif:
            new.exif_orientation = EXIF_FLIP_MAP[direction][new.exif_orientation or 1]
        new._update_thumbnail()
        return new

    def transpose(self, with_exif=False):
        """ Transpose the image (across  upper-right -> lower-left axis)

        :return:        transposed image
        :rtype:         jpegtran.JPEGImage

        """
        new = JPEGImage(blob=lib.Transformation(self.data).transpose())
        if with_exif:
            new.exif_orientation = EXIF_TRANSPOSE_MAP[new.exif_orientation or 1]
        new._update_thumbnail()
        return new

    def transverse(self, with_exif=False):
        """ Transverse transpose the image (across  upper-left -> lower-right
        axis)

        :return:        transverse transposed image
        :rtype:         jpegtran.JPEGImage

        """
        new = JPEGImage(blob=lib.Transformation(self.data).transverse())
        if with_exif:
            new.exif_orientation = EXIF_TRANVERSE_MAP[new.exif_orientation or 1]
        new._update_thumbnail()
        return new

    def crop(self, x, y, width, height):
        """ Crop a rectangular area from the image.

        :param x:       horizontal coordinate of upper-left corner
        :type x:        int
        :param y:       vertical coordinate of upper-left corner
        :type y:        int
        :param width:   width of area
        :type width:    int
        :param height:  height of area
        :type height:   int
        :return:        cropped image
        :rtype:         jpegtran.JPEGImage

        """
        valid_crop = (x < self.width and y < self.height and
                      x+width <= self.width and y+height <= self.height)
        if not valid_crop:
            raise ValueError("Crop parameters point outside of the image")
        new = JPEGImage(blob=lib.Transformation(self.data)
                             .crop(x, y, width, height))
        new._update_thumbnail()
        return new

    def downscale(self, width, height, quality=75):
        """ Downscale the image.

        :param width:   Scaled image width
        :type width:    int
        :param height:  Scaled image height
        :type height:   int
        :param quality: JPEG quality of scaled image (default: 75)
        :type quality:  int
        :return:        downscaled image
        :rtype:         jpegtran.JPEGImage

        """
        if width == self.width and height == self.height:
            return self
        if width > self.width or height > self.height:
            raise ValueError("jpegtran can only downscale JPEGs")
        new = JPEGImage(blob=lib.Transformation(self.data)
                        .scale(width, height, quality))
        new._update_thumbnail()
        return new

    def save(self, fname):
        """ Save the image to a file

        :param fname:   Path to file
        :type fname:    unicode

        """
        if not re.match(r'^.*\.jp[e]*g$', str(fname).lower()):
            raise ValueError("fname must refer to a JPEG file, i.e. end with "
                             "'.jpg' or '.jpeg'")
        with open(fname, 'wb') as fp:
            fp.write(self.data)

    def as_blob(self):
        """ Get the image data as a string

        :return:    Image data
        :rtype:     bytes

        """
        return bytes(self.data)

    def _update_thumbnail(self):
        if not self.exif_thumbnail:
            return
        target_width = None
        target_height = None
        if self.width > self.height:
            target_width = 160
            target_height = int(160/(self.width/self.height))
        else:
            target_height = 160
            target_width = int(160*(self.width/self.height))
        if target_width > self.width and target_height > self.height:
            # TODO: We should instead strip the thumbnail completely since
            #       it clearly no longer makes any sense
            return
        updated = self.downscale(target_width, target_height)
        self.exif_thumbnail = updated
