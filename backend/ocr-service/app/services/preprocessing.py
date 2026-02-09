import cv2
import numpy as np
from PIL import Image
import io

def preprocess_image(image_bytes: bytes, apply_all: bool = True) -> bytes:
    """
    Apply comprehensive preprocessing pipeline
    
    Steps:
    1. Grayscale conversion
    2. Noise reduction
    3. Binarization (Otsu's method)
    4. Skew correction
    """
    
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Failed to decode image")
    
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if not apply_all:
        is_success, buffer = cv2.imencode(".png", gray)
        return buffer.tobytes()
    
    # 2. Noise reduction
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # 3. Binarization (Otsu)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 4. Skew correction
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        if abs(angle) > 0.5:  # Only correct if skew is significant
            (h, w) = binary.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            corrected = cv2.warpAffine(
                binary, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
        else:
            corrected = binary
    else:
        corrected = binary
    
    # Convert back to bytes
    is_success, buffer = cv2.imencode(".png", corrected)
    if not is_success:
        raise ValueError("Failed to encode processed image")
    
    return buffer.tobytes()


def convert_pdf_to_images(pdf_bytes: bytes) -> list:
    """Convert PDF to list of image bytes"""
    from pdf2image import convert_from_bytes
    
    images = convert_from_bytes(pdf_bytes)
    image_bytes_list = []
    
    for img in images:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_bytes_list.append(img_byte_arr.getvalue())
    
    return image_bytes_list