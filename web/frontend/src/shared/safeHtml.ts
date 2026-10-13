import DOMPurify from 'dompurify';

/** Imported source is untrusted, even when delivered by our own API.
 * Keep this as the final operation before the HTML sink. */
export function sanitizeSourceHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'form', 'input', 'button', 'textarea', 'select', 'option', 'video', 'audio'],
    FORBID_ATTR: ['style', 'srcset', 'formaction', 'autofocus'],
    ALLOW_DATA_ATTR: false,
    SANITIZE_NAMED_PROPS: true,
  });
}
