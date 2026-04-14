### Anthropic

Anthropic has been an aggressive buyer in the RL environment market. Anthropic is often the first customer of dozens of new companies, providing them with exclusive contracts and in some cases tips on environment construction. We think they are working with more than a dozen RL environment companies as contractors. The company likely wants a broad ecosystem of vendors such that the product is commoditized, driving down costs on some types of environments.

A lively vendor ecosystem also attracts investors who can further subsidize costs. The tradeoff is overhead from managing many vendors at once, which is why we believe Anthropic is requiring vendors to adhere to specific [sandbox frameworks in most domains](https://github.com/laude-institute/sandboxes) and has built a vendor engagement platform.

While it is correct that the company is focused on code, we are now seeing them start to ramp up on other domains. Computer use, for example, has been high on the priority list for some time now. Other areas, like biology, are also ramping, as we will show later. Coding is still central to their efforts, but is not the only domain they are interested in.

### OpenAI

We believe OpenAI buys from a smaller pool of vendors than Anthropic, though they outspend Anthropic and many other labs on net for data. To reduce reliance on third parties like Surge, Mercor, and Handshake, OpenAI is building an in-house human data team. xAI has taken a similar approach from the start, posting for AI tutors since the company launched and now ramping up that hiring.

They outspend the labs because they have many parallel areas they are trying to scale. ChatGPT Agent sees heavy use of UI Gyms. The model which won IMO Gold, a version of GPT-5.1 Codex Max, benefited from large amounts of math and code data. The consumer version sees a mix from all the programs in addition to targeted post-training around behaviour.

![](https://substackcdn.com/image/fetch/$s_!Mzol!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fec316bd5-13f2-4f91-971e-62102e1570ab_1446x840.png)

*Sample answer from the IMO winning model. Source: OpenAI*

Data across programs is aggregated and spun back into mid-training, which we will explain later. This increases performance across the board.

The large volumes of data OpenAI procures has played a key part in their post-training efforts, which as mentioned, have driven the key capabilities forward in the last several generations. As their human data team scales, they will be able to skip paying the margins to many of the data vendors and aggregate more data volume for the same cost.

### Google DeepMind

Google DeepMind’s procurement is rather decentralized. Environment procurement specifically has been driven by researchers from different teams and programs. Specific environments they have been interested in centralized around coding and computer use, particularly ML related environments and tasks.

Google spent a small amount of compute on post-training for Gemini 2.5 Pro, likely under 5% of pre-training compute at launch. While they have scaled it up for Gemini 3, we still think it is small relative to the other labs. Nevertheless, Google is uniquely positioned for this paradigm: they already own the underlying platforms (Sheets, Slides, Docs, Drive, Maps) and don’t need to build new ones. More importantly, their legions of PMs have deep visibility into how hundreds of millions of users actually interact with these products, providing a direct signal for what strong model performance should look like. It is then mostly a matter of time and politics until Google utilizes this user behavior to post-train Gemini on those applications. This is harder for Google than if it was just a technical barrier.

Google has also been on the defensive, decreasing rate limits for scraping of their products like Gmail. This makes it harder for other to scrape the app and use the data for replication efforts (e.g., a mockup app to train with).

In the long run, though, how useful should we expect these models to be? Is the path to AGI just environments stacked on top of each other?
