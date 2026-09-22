/** Lazy TeX/SVG engine: no startup/menu/accessibility bundle or script loader.
 * Vite defines MathJax's PACKAGE_VERSION so its Node-only eval(require) branch
 * is eliminated in browser builds. Browser regression tests guard that boundary.
 */
import { mathjax } from 'mathjax-full/js/mathjax.js';
import { TeX } from 'mathjax-full/js/input/tex.js';
import { SVG } from 'mathjax-full/js/output/svg.js';
import { browserAdaptor } from 'mathjax-full/js/adaptors/browserAdaptor.js';
import { RegisterHTMLHandler } from 'mathjax-full/js/handlers/html.js';
import { AllPackages } from 'mathjax-full/js/input/tex/AllPackages.js';

let engine: { tex2svg: (latex: string, options: Record<string, unknown>) => HTMLElement } | null = null;

export function createEngine() {
  if (engine) return engine;
  const adaptor = browserAdaptor();
  RegisterHTMLHandler(adaptor);
  const tex = new TeX({
    packages: AllPackages.filter(name => name !== 'autoload' && name !== 'require'),
    maxBuffer: 32 * 1024,
    maxMacros: 1000,
  });
  const document = mathjax.document('', {
    InputJax: tex,
    OutputJax: new SVG({ fontCache: 'none' }),
  });
  engine = {
    tex2svg: (latex, options) => document.convert(latex, options) as HTMLElement,
  };
  return engine;
}
