对于 GB300，尽管参考设计配备了四个用于后端网络的 ConnectX-8 网卡（NIC）和一个用于前端网络的 Bluefield-3，但大多数超大规模云厂商（hyperscalers）都有自己的设计和替代网络配置，特别是针对 Bluefield-3。除了网络配置外，供电模块、本地 NVMe 存储和管理模块在不同客户之间也具有高度的定制化和差异化。

例如，在某些机柜中，甚至亚马逊（Amazon）在许多情况下也会在 GB300 中部署 ConnectX-8。此外，大多数超大规模云厂商在前端网络中部署的是其自研 DPU，而非 Bluefield-3。由于每家客户对这些模块的偏好不同，GB300 中的供电模块和管理模块也经过了高度定制。因此，GB300 的前半部分具有极高的可定制性，各家超大规模云厂商的设计之间存在显著差异。

https://substackcdn.com/image/fetch/$s_!RjLj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe84cedc7-fe5c-4781-99f8-1bf9cd135df9_2806x2341.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

对于 VR NVL72，虽然仍保留了一定程度的定制化空间，但在外形规格（form factor）上存在更多限制。鉴于 VR NVL72 采用模块化和无线缆设计，机箱前端的定制模块必须符合英伟达参考设计的外形规格和尺寸。可供定制的模块包括供电模块、Bluefield-4 和管理模块。我们预计大多数超大规模云厂商客户将采用其自研 DSP 而非 Bluefield-4。考虑到外形规格和尺寸的限制，超大规模云厂商正在重新设计其自研 DPU 的电路板布局和模块外形，以匹配 Bluefield-4。对于供电模块和管理模块，一些客户还计划将二者合二为一。

亚马逊确实为 VR NVL72 提供了一个 JBOK / Nitro Box 网卡版本。
