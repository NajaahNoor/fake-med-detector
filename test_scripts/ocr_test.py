import os

# PaddleOCR on this environment can hit a PaddlePaddle OneDNN runtime issue
# during CPU inference. Disabling OneDNN avoids the crash for this test.
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")

from paddleocr import PaddleOCR
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False)

# Run OCR inference on a sample image 
result = ocr.predict(
    input="/home/rayaden/Downloads/WhatsApp Image 2026-05-14 at 6.57.51 PM.jpeg")
# Visualize the results and save the JSON results
for res in result:
    res.print()
    res.save_to_img("output")
    res.save_to_json("output")
