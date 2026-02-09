from google.cloud import vision

client = vision.ImageAnnotatorClient()

def extract_with_google_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract text from a multi-page PDF using Google Cloud Vision
    """

    input_config = vision.InputConfig(
        content=pdf_bytes,
        mime_type="application/pdf"
    )

    feature = vision.Feature(
        type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
    )

    request = vision.AnnotateFileRequest(
        input_config=input_config,
        features=[feature]
    )

    response = client.batch_annotate_files(requests=[request])

    if response.responses[0].error.message:
        raise Exception(response.responses[0].error.message)

    full_text = []

    # Loop over pages
    for page_response in response.responses[0].responses:
        if page_response.full_text_annotation:
            full_text.append(page_response.full_text_annotation.text)

    return {
        "text": "\n".join(full_text).strip(),
        "confidence": None,
        "engine": "google",
        "pages": len(response.responses[0].responses)
    }
