# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 13:47:50 2024

@author: Grisha Spektor
"""
from PIL import Image, ImageOps
import numpy as np
from scipy.ndimage import rotate

class ImageModel:
    def __init__(self):
        self.image = None
        self.rotated_image = None  # Store the rotated image
        self.rotation_angle = 0

    def load_image(self, file_path):
        print(f"Loading image from {file_path}")
        self.image = Image.open(file_path)
        self.rotated_image = self.image  # Initially, no rotation
        print(f"Image loaded: {self.image}")
        return self.image

    def get_image(self):
        return self.image

    def rotate_image(self, angle):
        self.rotation_angle = float(angle)
        if self.image:
            rotated_image = ImageOps.exif_transpose(self.image)
            rotated_image = Image.fromarray(rotate(np.array(rotated_image), self.rotation_angle, reshape=False))
            self.rotated_image = rotated_image  # Update the rotated image
            return rotated_image
        return None

    def get_line_profile(self, y):
        if self.rotated_image:
            image_array = np.array(self.rotated_image)
            line_profile = image_array[y, :]
            print(f"Extracted line profile at y={y}: {line_profile}")  # Debug statement
            return line_profile
        return None
