import os
import sys

# Put the b2b/ root on sys.path so `sigma_core...` imports resolve when running
# pytest from anywhere. (No installed package; this mirrors PYTHONPATH=b2b.)
sys.path.insert(0, os.path.dirname(__file__))
