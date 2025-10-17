# -*- coding: utf-8 -*-
"""
Signature Watermark Utility
Adds watermarks to signature images to prevent unauthorized use
"""

import io
import base64
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from datetime import datetime


def add_watermark_to_signature(signature_data, watermark_text="SCHOOL USE ONLY", reference_number="", timestamp=None):
    """
    Add watermark to signature image

    Args:
        signature_data: Base64 encoded signature image
        watermark_text: Main watermark text (default: "SCHOOL USE ONLY")
        reference_number: Document reference number to include
        timestamp: Signature timestamp (datetime object)

    Returns:
        Base64 encoded watermarked image
    """
    if not signature_data:
        return signature_data

    try:
        # Decode image
        image_data = base64.b64decode(signature_data)
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGBA if needed
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Create watermark layer
        watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark)

        # Get image dimensions
        width, height = image.size

        # Try to use a standard font, fallback to default if not available
        try:
            # Try multiple font paths (works on different systems)
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                'C:/Windows/Fonts/arialbd.ttf',  # Windows fallback
            ]
            font_large = None
            font_small = None
            for font_path in font_paths:
                try:
                    font_large = ImageFont.truetype(font_path, int(height * 0.15))
                    font_small = ImageFont.truetype(font_path, int(height * 0.08))
                    break
                except:
                    continue
            if not font_large:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw diagonal "SCHOOL USE ONLY" watermark (large, faint)
        main_text = watermark_text

        # Create rotated text layer for diagonal watermark
        txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
        txt_draw = ImageDraw.Draw(txt_layer)

        # Calculate text size using textbbox
        bbox = txt_draw.textbbox((0, 0), main_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Draw text in center
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # Draw with semi-transparent red
        txt_draw.text((x, y), main_text, fill=(255, 0, 0, 60), font=font_large)

        # Rotate the text layer
        txt_layer = txt_layer.rotate(-20, expand=False)

        # Composite the rotated text onto watermark
        watermark = Image.alpha_composite(watermark, txt_layer)

        # Draw reference number and timestamp at bottom (small, readable)
        info_y = height - int(height * 0.12)

        if reference_number:
            ref_text = f"Ref: {reference_number}"
            draw = ImageDraw.Draw(watermark)
            draw.text((10, info_y), ref_text, fill=(80, 80, 80, 180), font=font_small)

        if timestamp:
            if isinstance(timestamp, str):
                time_text = timestamp
            else:
                time_text = timestamp.strftime("%Y-%m-%d %H:%M")
            draw = ImageDraw.Draw(watermark)

            # Calculate text width for right alignment
            bbox = draw.textbbox((0, 0), time_text, font=font_small)
            time_width = bbox[2] - bbox[0]

            draw.text((width - time_width - 10, info_y), time_text,
                     fill=(80, 80, 80, 180), font=font_small)

        # Composite watermark onto original image
        watermarked = Image.alpha_composite(image, watermark)

        # Convert back to RGB for JPEG
        if watermarked.mode == 'RGBA':
            rgb_image = Image.new('RGB', watermarked.size, (255, 255, 255))
            rgb_image.paste(watermarked, mask=watermarked.split()[3])
            watermarked = rgb_image

        # Save to bytes
        output = io.BytesIO()
        watermarked.save(output, format='PNG', quality=95)
        output.seek(0)

        # Encode to base64
        return base64.b64encode(output.getvalue())

    except Exception as e:
        # If watermarking fails, return original (with log warning in production)
        print(f"Watermark error: {e}")
        return signature_data


def create_signature_preview(signature_data, max_width=400, max_height=150):
    """
    Create a smaller preview version of signature (for list views)

    Args:
        signature_data: Base64 encoded signature image
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        Base64 encoded preview image with watermark
    """
    if not signature_data:
        return signature_data

    try:
        # Decode image
        image_data = base64.b64decode(signature_data)
        image = Image.open(io.BytesIO(image_data))

        # Resize maintaining aspect ratio
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        image.save(output, format='PNG', quality=90)
        output.seek(0)

        # Encode to base64
        preview_data = base64.b64encode(output.getvalue())

        # Add watermark to preview
        return add_watermark_to_signature(preview_data, watermark_text="PREVIEW")

    except Exception as e:
        print(f"Preview error: {e}")
        return signature_data
