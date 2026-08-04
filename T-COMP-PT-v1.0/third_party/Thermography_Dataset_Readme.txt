Title: Thermal Inspection Dataset for Defect Segmentation in CFRP Laminates

Description:
This dataset consists of thermal images and corresponding annotated segmentation masks obtained through a pulsed thermography (PT) inspection of a carbon fiber-reinforced polymer (CFRP) laminate. The dataset is designed to support research in defect detection, segmentation, and analysis in composite materials.

Dataset Details:

1. Material Information:
   - Material Type: Carbon/PEEK laminate
   - Fiber Volume Fraction: 61%
   - Stacking Lay-Up: [02/902]6
   - Dimensions: 100 × 100 mm

2. Defect Details:
   - Defect Type: Artificial Kapton tape inserts
   - Defect Sizes: 2 × 2 mm, 3 × 3 mm, 4 × 4 mm
   - Defect Depths:
     - D1: 0.13 mm
     - D2: 0.26 mm
     - D3: 0.39 mm
   - Defects were embedded in specific layers of the laminate during the moulding process to simulate internal flaws.

3. Inspection Methodology:
   - Technique: Pulsed thermography
   - Imaging Equipment: Midwave infrared (MWIR) camera
     - Resolution: 640 × 512 pixels
     - Frame Rate: 55 Hz
   - Process: A short, intense heat pulse was applied to the laminate's surface, and the MWIR camera captured thermal profiles over time. A total of 1,034 images were recorded, capturing temporal variations in surface defects.

4. Annotation Details:
   - Tool Used: VGG Image Annotator (VIA)
   - Annotation Output: Each image was manually labeled to generate segmentation masks that represent the ground truth for defect regions. These annotations were verified by experts to ensure accuracy.

5. Dataset Composition:
   - Original Images: 1,034 thermal images
   - Annotated Masks: 1,034 corresponding segmentation masks
   - The dataset allows for analysis of both spatial and temporal evolution of defects.

Applications:
This dataset is ideal for:
- Training and validating machine learning models for defect detection and segmentation.
- Temporal analysis of surface defects in composite materials.
- Advancing non-destructive testing (NDT) techniques for quality control in manufacturing.

Citation:
If you use this dataset, please credit the authors and reference the related publication. For further details or to access the dataset, please visit the repository or contact the authors.

Please reference this publication: 
Garcia Vargas, I., & Fernandes, H. (2025). Spatial and temporal deep learning algorithms for defect segmentation in infrared thermographic imaging of carbon fibre-reinforced polymers. Nondestructive Testing and Evaluation, 1–21. https://doi.org/10.1080/10589759.2025.2457593
