from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Any, Dict

DimsList = List[Tuple[int, int]]


class ResolutionsList(list):
    @staticmethod
    def round(a) -> int:
        """Rounding, as performed in WordPress, the "traditional" way."""
        return int(Decimal(a).quantize(0, ROUND_HALF_UP))

    def append(self, resolution: Tuple):
        rounded_resolution = (
            ResolutionsList.round(resolution[0]),
            ResolutionsList.round(resolution[1]))
        list.append(self, rounded_resolution)


class ImgScaler:
    def __init__(self, src_w: int, src_h: int,
                 med_w: int = 300, med_h: int = 300,
                 large_w: int = 1024, large_h: int = 1024,
                 thumb_w: int = 150, thumb_h: int = 150):
        """
        WordPress media settings contain a lot of options for various sizes.
        These apply only at upload time (if at all), pre-existing images
        are not affected by changes to those parameters. There are defaults
        because I don't believe the vast majority of WordPress users appreciate,
        notice, or alter these.

        :param src_w: source width
        :param src_h: source height
        :param med_w: medium width
        :param med_h: medium height
        :param large_w: large width
        :param large_h: large height
        :param thumb_w: thumbnail width
        :param thumb_h: thumbnail height
        :return: 2-tuple of generated sizes and a separate thumbnail size, if
            applicable, because that is zoom cropped unlike the rest.
        """
        self.src_w = src_w
        self.src_h = src_h
        self.med_w = med_w
        self.large_w = large_w
        self.thumb_w = thumb_w
        self.med_h = med_h
        self.large_h = large_h
        self.thumb_h = thumb_h

    def get_widths_and_heights(self) -> \
            Tuple[DimsList, Tuple[int, int]]:
        """
        :return: 2-tuple of generated sizes and a separate thumbnail size, if
            applicable, because that is zoom cropped unlike the rest.
        """
        MED_LARGE_W = 768
        w_hs = ResolutionsList()
        # 768 isn't optional!
        if self.src_w > MED_LARGE_W:
            w_hs.append(self.fix_width(MED_LARGE_W))
        thmb = self.get_thumbnail(self.thumb_w, self.thumb_h)
        self.add_scaled_size_bounded_by(w_hs, self.med_w, self.med_h)
        self.add_scaled_size_bounded_by(w_hs, self.large_w, self.large_h)
        # WordPress v.5.3 introduced three new large resized image sizes
        # https://wpo.plus/wordpress/large-image-sizes/
        # Currently, these are "named": "1536x1536" and "2048x2048" in the SQL.
        # I haven't seen a 2560 yet!
        self.add_scaled_size_bounded_by(w_hs, 1536, 1536)
        self.add_scaled_size_bounded_by(w_hs, 2048, 2048)
        # 2560x2560 wasn't being added, to a 4000x3000 original for example.
        # add_scaled_size_bounded_by(w_hs, src_w, src_h, 2560, 2560)
        return sorted(w_hs), thmb

    def get_thumbnail(self, thumb_w: int, thumb_h: int):
        if self.src_w >= thumb_w or self.src_h >= thumb_h:
            # This, thumbnail, is the only cropping transform (by default).
            # The other size all scale instead.
            if self.src_w < thumb_w and self.src_h < thumb_h:
                return
            if self.src_w < thumb_w:
                thumb_w = self.src_w
            if self.src_h < thumb_h:
                thumb_h = self.src_h
            return thumb_w, thumb_h

    def add_scaled_size_bounded_by(
            self, w_hs: ResolutionsList, max_w: int, max_h: int):
        if self.src_w > max_w or self.src_h > max_h:
            w_over = float(self.src_w) / max_w
            h_over = float(self.src_h) / max_h
            constraint = max(w_over, h_over)
            w_hs.append((self.src_w / constraint, self.src_h / constraint))

    def fix_width(self, fixed_width: int) -> Tuple[int, int]:
        return fixed_width, ResolutionsList.round(
            float(self.src_h) * fixed_width / self.src_w)
