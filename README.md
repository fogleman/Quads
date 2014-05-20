## Quads

Computer art based on quadtrees.

The program targets an input image. The input image is split into four quadrants. Each quadrant is assigned an averaged color based on the colors in the input image. The quadrant with the largest error is split into its four children quadrants to refine the image. This process is repeated N times.

### Web Demo

A web-based version can be seen here:

http://www.michaelfogleman.com/static/quads/

### Animation

The first animation shows the natural iterative process of the algorithm.

![Animation](http://i.imgur.com/UE2eOkx.gif)

The second animation shows a top-down, breadth-first traversal of the final quadtree.

![Animation](http://i.imgur.com/l3sv0In.gif)

### Samples

![Flower](http://i.imgur.com/RomAaw7.png)

![Flower](http://i.imgur.com/kjosmto.png)

![Apple](http://i.imgur.com/IiPaYO7.png)

![Apple](http://i.imgur.com/ZB83zVM.png)

![Butterfly](http://i.imgur.com/ujiZTwx.png)

![Lenna](http://i.imgur.com/OFdLCrD.png)

![Landscape](http://i.imgur.com/mBQAXFp.png)

![Zebra](http://i.imgur.com/iwyUHFR.png)

![Fractal](http://i.imgur.com/WJmHRcV.png)

![Mario](http://i.imgur.com/QvYyT3V.gif)
