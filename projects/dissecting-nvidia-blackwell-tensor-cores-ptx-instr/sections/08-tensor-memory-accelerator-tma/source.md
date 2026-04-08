TMA (PTX: `cp.async.bulk.tensor`, SASS: `UTMALDG`) is an asynchronous data copy engine introduced in the Hopper generation, specialized for moving large amounts of data from global memory to shared memory. A single thread can initiate TMA to perform address generation, memory swizzling, and out-of-bounds handling, freeing up other threads to execute independent work. Here we benchmark the 2D tensor version (cp.async.bulk.tensor.2d) to represent typical TMA usage.

Referencing FlashInfer attention kernels, we benchmark TMA, assigning only one CTA per SM but using one thread for each of 1 to 4 warps per CTA to issue TMA instructions of varying box sizes. The below graph shows the best-case throughput for each bytes-in-flight.

We benchmark TMA with the following configuration:

* CTAs per SM: 1

* Threads per CTA: 128 (4 warps)

* TMA box dimensions: 2D shapes increasing from size 32x8 to 128x128

![](https://substackcdn.com/image/fetch/$s_!IhCY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7a47a042-7c59-4cc1-8459-665852a23321_1600x720.png)

Peak throughput is reached far later than `LDGSTS`.
