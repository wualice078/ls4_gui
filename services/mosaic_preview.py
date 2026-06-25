"""Convert FITS mosaic files to browser-friendly PNG previews."""

from __future__ import annotations

from pathlib import Path


def fits_to_png(fits_path: Path, png_path: Path) -> bool:
    try:
        from astropy.io import fits
        import numpy as np
    except ImportError:
        return False

    try:
        data = fits.getdata(fits_path)
        if data is None:
            return False
        array = np.asarray(data, dtype=float)
        while array.ndim > 2:
            array = array[0]

        finite = array[np.isfinite(array)]
        if finite.size == 0:
            return False

        low, high = np.percentile(finite, [5, 99])
        if high <= low:
            high = low + 1.0
        scaled = np.clip((array - low) / (high - low), 0.0, 1.0)

        png_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image

            Image.fromarray((scaled * 255).astype("uint8"), mode="L").save(png_path)
            return True
        except ImportError:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.imsave(png_path, scaled, cmap="gray")
            return True
    except Exception:
        return False
