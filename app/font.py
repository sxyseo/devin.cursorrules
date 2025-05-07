import matplotlib
from matplotlib import font_manager
 
font_list=sorted([f.name for f in matplotlib.font_manager.fontManager.ttflist])
for i in font_list:
    print(i)
