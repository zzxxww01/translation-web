Fibers come out of the OE for the data to transmit. One optical lane is comprised of two fibers or one fiber pair (transmit plus receive). Fiber coupling – aligning the fibers precisely with on-chip waveguides for smooth and efficient light transmission – is a crucial and challenging step in CPO, and Fiber Array Units (“FAUs”) are widely used in CPO to assist in that process. There are two main ways to do this, namely edge coupling (EC) and grating coupling (GC).

### Edge Coupling

Edge coupling aligns the fiber along the chip’s edge. From the image below, we can see that the fiber end must be precisely aligned with the polished edge of the chip to ensure that the light beam enters the edge coupler accurately. A microlens at the fiber tip focuses and directs the light toward the chip, leading its entry into the waveguide. The waveguide taper gradually widens, allowing for a smooth mode transition that reduces reflections and scattering to ensure coupling efficiency. Without such a lens and taper, there will be significant optical loss at the interface between fiber facet and waveguide facet.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_038.png)

Source: Ansys

Edge coupling is favored for its low coupling loss, ability to work with a wide range of wavelengths, and polarization insensitivity. However, it also comes with a few disadvantages:

1. The fabrication process is more complex, and requires undercut and deep etching; 2. Fiber density can be limited because it’s a 1D structure; 3. It is incompatible with die stacking (as TSV needs thinning); 4. Challenges on mechanics reliability on form factor, mechanical stress, warpage, and fiber handling; 5. It offers less thermal reliability; and 6. There is a lack of ecosystem compatibility in general.

Global Foundries (GFS) demonstrated a monolithically integrated SiN edge coupler that enables 32 channels and 127µm-pitches on its signature 45nm “Fotonix” platform at this year’s VLSI conference.

### Grating Coupling (GC)

In grating couplers (GCs), light enters from the top and the fiber is positioned at a small angle above the grating. As the light reaches the grating, the periodic structure scatters and bends the light downward into the waveguides.

The major benefit of grating/vertical coupling is the ability to have multiple rows of fibers, allowing more fibers per optical engine. GCs also do not need to be placed at the bottom of the substrate, making it possible to place the OE on the interposer. Lastly, GC does not need to be positioned with extreme precision and it can be more easily manufactured with a simple two-step etched process. The drawbacks of GC is that single-polarization grating couplers only work for a limited range of wavelengths and are highly polarization sensitive.

Nvidia had a preference for GC due to its several advantages – it enables 2D density, offers a smaller footprint, is easier to manufacture, and allows for simpler wafer-level testing compared to EC. However, the company is also aware of GC’s several drawbacks – it generally introduces higher optical loss and has a narrower optical bandwidth than EC (the latter can generally accommodate a broader spectral range).

TSMC also clearly has a higher preference for GC, which is supported in their COUPE platform.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_039.png)

Source: Journal of Semiconductors
