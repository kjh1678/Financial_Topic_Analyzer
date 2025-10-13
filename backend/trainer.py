from collections import Counter
import pickle
import json
from pathlib import Path
import pandas as pd
from preprocessor import TextPreprocessor, DatabaseLoader
from gensim import corpora
from gensim.models import LdaModel

try:
    import gensim
    print(f"Gensim 설치됨: 버전 {gensim.__version__}")
except ImportError:
    print("Gensim이 설치되지 않았습니다.")