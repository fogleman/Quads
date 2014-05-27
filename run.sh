rm frames/*
python main.py $1
convert -loop 0 -delay 20 frames/*.png -delay 200 output.png output.gif
