In the spirit of open source, all runs occur on GitHub Actions, so benchmark results are verifiable, transparent, and reproducible. However, GitHub outages have been a constant obstacle to our goals recently. [We have seen more unicorns lately than any other animal](https://github.com/503.html)! But maybe it’s time for us to touch some grass.

Microsoft/GitHub themselves are aware of this and have stopped updating its status page with aggregate uptime numbers and are down to a single 9: 97.36% over the past 90 days. The problem doesn’t seem to go away if you choose to ignore it...

![](https://substackcdn.com/image/fetch/$s_!0uH0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3b921859-49f3-4b0b-b02e-dd0bf7a36e2e_3000x975.png)

Source: [Outages project](https://github.com/outages/github-outages)

![](https://substackcdn.com/image/fetch/$s_!mh4e!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdd7aad58-ba30-4364-9565-980ae6464534_3000x975.png)

Source: [Outages project](https://github.com/outages/github-outages)

All in all, GitHub Actions is just alright. It provides a painfully average experience for developers. It is certainly not meant for launching thousands of jobs across a fleet of hundreds of GPUs. Nevertheless, we have worked closely with some GitHub Actions engineers since our launch to better meet the needs of InferenceX, and we can confidently say they have been a pleasure to work with. Moreover, one of our direct asks was to implement lazy loading for jobs when clicking on a workflow run and, while it did take them a while, [they eventually implemented the feature.](http://github.blog/changelog/2025-12-22-improved-performance-for-github-actions-workflows-page/)
