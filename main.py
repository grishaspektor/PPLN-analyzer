# -*- coding: utf-8 -*-
"""
Created on Tue Aug  6 14:23:23 2024

@author: Grisha Spektor
"""
import tkinter as tk
from model import ImageModel
from view import ImageView
from controller import ImageController

def main():
    root = tk.Tk()
    model = ImageModel()
    controller = ImageController(model, view=None)  # Initialize controller with a temporary None for view
    view = ImageView(root, controller)
    controller.view = view  # Set the actual view reference in the controller
    root.mainloop()

if __name__ == "__main__":
    main()


