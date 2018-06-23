import pandas as pd
import numpy as np
import unidecode
pd.options.display.max_columns = 999
pd.options.display.max_rows = 999


import time
import unicodedata

import datetime
from datetime import timedelta, datetime

import csv
import os

import sys
sys.path.append('./lib/')
from functions import *

from tqdm import tnrange, tqdm_notebook
from unidecode import unidecode

import matplotlib
import numpy as np
import matplotlib.pyplot as plt

import seaborn as sns
sns.set_style("darkgrid")

import locale
locale.setlocale(locale.LC_ALL, 'es_ES')

from plotly import __version__
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import glob
