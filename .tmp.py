import os
from PIL import Image


def resize_imagge(image, ideal_width=800, ideal_height=450):
    """Resize and crop image to fit ideal dimensions, preserving aspect ratio.

    Args:
        image (PIL.Image.Image): Input image.
        ideal_width (int, optional): Desired width (default: 800).
        ideal_height (int, optional): Desired height (default: 450).

    Returns:
        PIL.Image.Image: Resized and cropped image.

    Note:
        Resizes while preserving aspect ratio. Crops to ideal aspect ratio,
        then resizes to desired dimensions. Lanczos resampling maintains
            quality.

    Example:
        >>> from PIL import Image
        >>> image = Image.open('input.jpg')
        >>> resized = resize_image(image, ideal_width=800, ideal_height=600)
        >>> resized.save('output.jpg')
    """

    width = image.size[0]
    height = image.size[1]

    aspect = width / float(height)
    ideal_aspect = ideal_width / float(ideal_height)

    if aspect > ideal_aspect:
        # Then crop the left and right edges
        new_width = int(ideal_aspect * height)
        offset = (width - new_width) / 2
        resize = (offset, 0, width - offset, height)
    else:
        # Crop the top and bottom
        new_height = int(width / ideal_aspect)
        offset = (height - new_height) / 2
        resize = (0, offset, width, height - offset)

    resized_image = image.crop(resize).resize(
        (ideal_width, ideal_height), Image.Resampling.LANCZOS
    )

    return resized_image


to_show = resize_imagge(
    image=Image.open(os.path.join(os.path.dirname(__file__), "splash_test.png"))
)
to_show.show()
